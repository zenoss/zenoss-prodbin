###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""SshClient runs commands on a remote box using SSH and
returns their results.

See http://twistedmatrix.com/trac/wiki/Documentation for Twisted documentation,
specifically documentation on 'conch' (Twisted's SSH protocol support).
"""

import os
import sys
import logging
log = logging.getLogger("zen.SshClient")

import Globals

from twisted.conch.ssh import transport, userauth, connection
from twisted.conch.ssh import common, keys, channel
from twisted.internet import defer, reactor
from Products.ZenEvents import Event
from Products.ZenUtils.Utils import getExitMessage

from Exceptions import *

import CollectorClient

# NB: Most messages returned back from Twisted are Unicode.
#     Expect to use str() to convert to ASCII before dumping out. :)


def sendEvent( self, message="", device='', severity=Event.Error ):
    """
    Shortcut version of sendEvent()

    @param message: message to send in Zenoss event
    @type message: string
    @param device: hostname of device to which this event is associated
    @type device: string
    @param severity: Zenoss severity from Products.ZenEvents
    @type severity: integer
    """

    # Parse out the daemon's name
    component= os.path.basename( sys.argv[0] ).replace( '.py', '' )

    def hasattr_path( object_root, path ):
        """
        The regular hasattr() only works on one component,
        not multiples.

        @param object_root: object to start searching for path
        @type object_root: object
        @param path: path to func or variable (eg "conn.factory" )
        @type path: string
        @return: is object_root.path sane?
        @rtype: boolean
        """
        obj = object_root
        for chunk in path.split('.'):
            obj= getattr( obj, chunk, None )
            if obj is None:
                return False
        return True

    # ... and the device's name (as known by Zenoss)
    if device == '':
       if hasattr_path( self, "factory.hostname" ):
           device= self.factory.hostname

       elif hasattr_path( self, "conn.factory.hostname" ):
           device= self.conn.factory.hostname

       else:
           log.debug( "Couldn't get the remote device's hostname" )

    error_event= {
       'agent': component,
       'summary': message,
       'device': device,
       'eventClass': "/Cmd/Fail",
       'component': component,
       'severity': severity,
    }

    # At this point, we don't know what we have
    try:
        if hasattr_path( self, "factory.datacollector.sendEvent" ):
            self.factory.datacollector.sendEvent( error_event )

        elif hasattr_path( self, "datacollector.sendEvent" ):
            self.datacollector.sendEvent( error_event )

        elif hasattr_path( self, "conn.factory.datacollector.sendEvent" ):
            self.conn.factory.datacollector.sendEvent( error_event )

        else:
            log.debug( "Unable to send event for %s" % error_event )

    except:
        pass # Don't cause other issues



class SshClientError( Exception ):
    """
    Exception class
    """



class SshClientTransport(transport.SSHClientTransport):
    """
    Base client class for constructing Twisted Conch services.
    This class is *only* responsible for connecting to the SSH
    service on the device, and ensuring that *host* keys are sane.
    """

    def verifyHostKey(self, hostKey, fingerprint):
        """
        Module to verify the host's SSH key against the stored fingerprint we have
        from the last time that we communicated with the host.

        NB: currently does not verify this information but simply trusts every host key

        @param hostKey: host's SSH key (unused)
        @type hostKey: string
        @param fingerprint: host fingerprint (unused)
        @type fingerprint: string
        @return: Twisted deferred object
        @rtype: Twisted deferred object (defer.succeed(1)
        @todo: verify the host key
        """
        #blowing off host key right now, should store and check
        from Products.ZenUtils.Utils import unused
        unused(hostKey)
        log.debug('%s host fingerprint: %s' % (self.factory.hostname, fingerprint))
        return defer.succeed(1)


    def connectionMade(self):
        """
        Called after the connection has been made.
        Used to set up private instance variables.
        """
        self.factory.transport = self.transport
        transport.SSHClientTransport.connectionMade(self)


    def receiveError( self, reasonCode, description ):
        """
        Called when a disconnect error message was received from the device.

        @param reasonCode: error code from SSH connection failure
        @type reasonCode: integer
        @param description: human-readable version of the error code
        @type description: string
        """
        message= 'SSH error from remote device (code %d): %s\n' % \
                 ( reasonCode, str( description ) )
        log.warn( message )
        sendEvent( self, message=message )
        transport.SSHClientTransport.receiveError(self, reasonCode, description )


    def receiveUnimplemented( self, seqnum ):
        """
        Called when an unimplemented packet message was received from the device.

        @param seqnum: SSH message code
        @type seqnum: integer
        """
        message= "Got 'unimplemented' SSH message, seqnum= %d" % seqnum
        log.info( message )
        sendEvent( self, message=message )
        transport.SSHClientTransport.receiveUnimplemented(self, seqnum)


    def receiveDebug( self, alwaysDisplay, message, lang ):
        """
        Called when a debug message was received from the device.

        @param alwaysDisplay: boolean-type code to indicate if the message is to be displayed
        @type alwaysDisplay: integer
        @param message: debug message from remote device
        @type message: string
        @param lang: language code
        @type lang: integer
        """
        message= "Debug message from remote device (%s): %s" % ( str(lang), str(message) )
        log.info( message )
        sendEvent( self, message=message, severity=Event.Debug )

        transport.SSHClientTransport.receiveDebug(self, alwaysDisplay, message, lang )


    def connectionSecure(self):
        """
        This is called after the connection is set up and other services can be run.
        This function starts the SshUserAuth client (ie the Connection client).
        """
        sshconn = SshConnection(self.factory)
        sshauth = SshUserAuth(self.factory.username, sshconn, self.factory)
        self.requestService(sshauth)



class SshUserAuth(userauth.SSHUserAuthClient):
    """
    Class to gather credentials for use with our SSH connection,
    and use them to authenticate against the remote device.
    """

    def __init__(self, user, instance, factory):
        """
        If no username is supplied, defaults to the user running this code (eg zenoss)

        @param user: username
        @type user: string
        @param instance: instance object
        @type instance: object
        @param factory: factory info
        @type factory: Twisted factory object
        """
        user = str(user)                # damn unicode
        if user == '':
            log.debug( "Unable to determine username/password from " + \
                       "zCommandUser/zCommandPassword" )

            # From the Python docs about the preferred method of 
            # obtaining user name in preference to os.getlogin()
            #  (http://docs.python.org/library/os.html)
            import pwd
            try:
                user = os.environ.get( 'LOGNAME', pwd.getpwuid(os.getuid())[0] )
            except:
                pass

            if user == '':
                message= "No zProperties defined and unable to determine current user."
                log.error( message )
                sendEvent( self, message=message )
                raise SshClientError( message )

        userauth.SSHUserAuthClient.__init__(self, user, instance)
        self.user = user
        self.factory = factory


    def getPassword(self, unused=None):
        """
        Return a deferred object of success if there's a password or
        return fail (ie no zCommandPassword specified)

        @param unused: unused (unused)
        @type unused: string
        @return: Twisted deferred object (defer.succeed or defer.fail)
        @rtype: Twisted deferred object
        """

        if not self.factory.password:
            message= "SshUserAuth: no password found -- " + \
                     "has zCommandPassword been set?"
            log.error( message )
            sendEvent( self, message=message )
            self.factory.clientFinished()
            return defer.fail( SshClientError( message ) )

        else:
            return defer.succeed(self.factory.password)


    def getPublicKey(self):
        """
        Return the SSH public key (using the zProperty zKeyPath) or None

        @return: SSH public key
        @rtype: string
        """
        keyPath = os.path.expanduser( self.factory.keyPath )
        log.debug('Expanded SSH public key path from zKeyPath %s to %s' % ( self.factory.keyPath, keyPath))

        path = None
        if os.path.exists(keyPath):
            path = keyPath
        else:
            log.debug( "SSH public key path %s doesn't exist" % keyPath )
            return

        return keys.getPublicKeyString( path + '.pub' )


    def ssh_USERAUTH_FAILURE( self, packet):
        """
        Called when the SSH session can't authenticate.
        NB: This function is also called as an initializer
            to start the connections.

        @param packet: returned packet from the host
        @type packet: object
        """
        from twisted.conch.ssh.common import getNS
        canContinue, partial = getNS(packet)
        canContinue = canContinue.split(',')

        from Products.ZenUtils.Utils import unused
        unused(partial)

        lastAuth= getattr( self, "lastAuth", '')
        if lastAuth == '' or lastAuth == 'none':
            pass   # Start our connection

        elif lastAuth == 'publickey':
            self.authenticatedWith.append(self.lastAuth)
            message= "SSH login to %s with SSH keys failed" % \
                      self.factory.hostname
            log.error( message )
            sendEvent( self, message=message )

        elif lastAuth == 'password':
            message= "SSH login to %s with username %s failed" % \
                     ( self.factory.hostname, self.user )
            log.error( message )
            sendEvent( self, message=message )

            self.factory.loginTries -= 1
            log.debug( "Decremented loginTries count to %d" % self.factory.loginTries )

            if self.factory.loginTries <= 0:
                message= "SSH connection aborted after maximum login attempts."
                log.error( message )
                sendEvent( self, message=message )

            else:
                return self.tryAuth('password')


            self.authenticatedWith.append(self.lastAuth)

        # Straight from the nasty Twisted code
        def _(x, y):
            try:
                i1 = self.preferredOrder.index(x)
            except ValueError:
                return 1
            try:
                i2 = self.preferredOrder.index(y)
            except ValueError:
                return -1
            return cmp(i1, i2)

        canContinue.sort(_)
        log.debug( 'Sorted list of authentication methods: %s' % canContinue)
        for method in canContinue:
            if method not in self.authenticatedWith:
                log.debug( "Attempting method %s" % method )
                if self.tryAuth(method):
                    return

        log.debug( "All authentication methods attempted" )
        self.factory.clientFinished()
        self.transport.sendDisconnect(transport.DISCONNECT_NO_MORE_AUTH_METHODS_AVAILABLE, 'No more authentication methods available')



    def getPrivateKey(self):
        """
        Return a deferred with the SSH private key (using the zProperty zKeyPath)

        @return: Twisted deferred object (defer.succeed)
        @rtype: Twisted deferred object
        """

        keyPath = os.path.expanduser(self.factory.keyPath)
        log.debug('Expanded SSH private key path from zKeyPath %s to %s' % ( self.factory.keyPath, keyPath))
        path = None
        if os.path.exists(keyPath):
            path = keyPath
        else:
            log.debug( "SSH private key path %s doesn't exist" % keyPath )

        return defer.succeed(keys.getPrivateKeyObject(path,
                passphrase=self.factory.password))



class SshConnection(connection.SSHConnection):
    """
    Wrapper class that starts channels on top of connections.
    """

    def __init__(self, factory):
        """
        Initializer

        @param factory: factory containing the connection info
        @type factory: Twisted factory object
        """
        log.debug( "Creating new SSH connection..." )
        connection.SSHConnection.__init__(self)
        self.factory = factory


    def ssh_CHANNEL_FAILURE( self, packet):
        """
        Called when the SSH session can't authenticate

        @param packet: returned packet from the host
        @type packet: object
        """
        message= "CHANNEL_FAILURE: Authentication failure"
        log.error( message )
        sendEvent( self, message=message )
        connection.SSHConnection.ssh_CHANNEL_FAILURE( self, packet )


    def ssh_CHANNEL_OPEN_FAILURE( self, packet):
        """
        Called when the SSH session can't authenticate

        @param packet: returned packet from the host
        @type packet: object
        """
        message= "CHANNEL_OPEN_FAILURE: Authentication failure"
        log.error( message )
        sendEvent( self, message=message )
        connection.SSHConnection.ssh_CHANNEL_OPEN_FAILURE( self, packet )


    def ssh_REQUEST_FAILURE( self, packet):
        """
        Called when the SSH session can't authenticate

        @param packet: returned packet from the host
        """
        message= "REQUEST_FAILURE: Authentication failure"
        log.error( message )
        sendEvent( self, message=message )
        connection.SSHConnection.ssh_REQUEST_FAILURE( self, packet )


    def openFailed(self, reason):
        """
        Called when the connection open() fails.
        Usually this gets called after too many bad connection attempts,
        and the remote device gets upset with us.

        NB: reason.desc is the human-readable description of the failure
            reason.code is the SSH error code
         (see http://tools.ietf.org/html/rfc4250#section-4.2.2 for more details)

        @param reason: reason object
        @type reason: reason object
        """

        message= 'SSH connection to %s failed (error code %d): %s' % \
                 (self.command, reason.code, str(reason.desc) )
        log.error( message )
        sendEvent( self, message=message )
        connection.SSHConnection.openFailed( self, reason )


    def serviceStarted(self):
        """
        Called when the service is active on the transport
        """
        self.factory.serviceStarted(self)


    def addCommand(self, cmd):
        """
        Open a new channel for each command in queue

        @param cmd: command to run
        @type cmd: string
        """
        ch = CommandChannel(cmd, conn=self)
        self.openChannel(ch)


    def channelClosed(self, channel):
        """
        Called when a channel is closed.
        REQUIRED function by Twisted.

        @param channel: channel that closed
        @type channel: Twisted channel object
        """
        # grr.. patch SSH inherited method to deal with partially
        # configured channels
        self.localToRemoteChannel[channel.id] = None
        self.channelsToRemoteChannel[channel] = None
        connection.SSHConnection.channelClosed(self, channel)



class CommandChannel(channel.SSHChannel):
    """
    The class that actually interfaces between Zenoss and the device.
    """

    name = 'session'

    def __init__(self, command, conn=None):
        """
        Initializer

        @param command: command to run
        @type command: string
        @param conn: connection to create the channel on
        @type conn: Twisted connection object
        """
        channel.SSHChannel.__init__(self, conn=conn)
        self.command = command
        self.exitCode = None
        log.debug( "Started the channel for command: %s" % command )


    def openFailed(self, reason):
        """
        Called when the open fails.
        """
        from twisted.conch.error import ConchError
        if isinstance(reason, ConchError):
            args = (reason.data, reason.value)
        else:
            args = (reason.code, reason.desc)
        message = 'Open of %s failed (error code %d): %s' % (
                (self.command,) + args)
        log.warn(message)
        sendEvent(self, message=message)
        channel.SSHChannel.openFailed(self, reason)


    def extReceived(self, dataType, data ):
        """
        Called when we receive extended data (usually standard error)

        @param dataType: data type code
        @type dataType: integer
        """
        message= 'The command %s returned stderr data (%d) from the device: %s' \
                 % (self.command, dataType, data)
        log.warn( message )
        sendEvent( self, message=message )


    def channelOpen(self, unused):
        """
        Initialize the channel and send our command to the device.

        @param unused: unused (unused)
        @type unused: string
        @return: Twisted channel
        @rtype: Twisted channel
        """

        log.debug('Opening command channel for %s' % self.command)
        self.data = ''

        #  Notes for sendRequest:
        # 'exec'      - execute the following command and exit
        # common.NS() - encodes the command as a length-prefixed string
        # wantReply   - reply to let us know the process has been started
        d = self.conn.sendRequest(self, 'exec', common.NS(self.command),
                                  wantReply=1)
        return d


    def request_exit_status(self, data):
        """
        Gathers the exit code from the device

        @param data: returned value from device
        @type data: packet
        """
        import struct
        self.exitCode = struct.unpack('>L', data)[0]
        log.debug("Exit code for %s is %d: %s",
                  self.command,
                  self.exitCode,
                  getExitMessage(self.exitCode))


    def dataReceived(self, data):
        """
        Response stream from the device.  Can be called multiple times.

        @param data: returned value from device
        @type data: string
        """
        self.data += data


    def closed(self):
        """
        Cleanup for the channel, as both ends have closed the channel.
        """

        log.debug('Closed command channel for command %s with data: %s' % \
                   (self.command, repr(self.data)))
        self.conn.factory.addResult(self.command, self.data, self.exitCode)
        self.loseConnection()

        if self.conn.factory.commandsFinished():
            self.conn.factory.clientFinished()



class SshClient(CollectorClient.CollectorClient):
    """
    SSH Collector class to connect to a particular device
    """

    def __init__(self, hostname, ip, port=22, plugins=[], options=None,
                    device=None, datacollector=None ):
        """
        Initializer

        @param hostname: hostname of the device
        @type hostname: string
        @param ip: IP address of the device
        @type ip: string
        @param port: port number to use to connect to device
        @type port: integer
        @param plugins: plugins
        @type plugins: list of plugins
        @param options: options
        @type options: list
        @param device: name of device
        @type device: string
        @param datacollector: object
        @type datacollector: object
        """

        CollectorClient.CollectorClient.__init__(self, hostname, ip, port,
                           plugins, options, device, datacollector)
        self.hostname = hostname
        self.protocol = SshClientTransport
        self.connection = None
        self.transport = None


    def run(self):
        """
        Start SSH collection.
        """
        reactor.connectTCP(self.ip, self.port, self, self.loginTimeout)


    def serviceStarted(self, sshconn):
        """
        Run commands that are in the command queue

        @param sshconn: connection to create channels on
        @type sshconn: Twisted SSH connection
        """

        log.info("Connected to device %s" % self.hostname)
        self.connection = sshconn
        for cmd in self.getCommands():
            sshconn.addCommand(cmd)


    def addCommand(self, commands):
        """
        Add a command or commands to queue and open a command
        channel for each command

        @param commands: commands to run
        @type commands: list
        """

        CollectorClient.CollectorClient.addCommand(self, commands)
        if type(commands) == type(''):
            commands = (commands,)

        # The following code never gets called, AFAIK
        if self.connection:
            for cmd in commands:
                self.connection.addCommand(cmd)


    def clientConnectionFailed( self, connector, reason ):
        """
        If we didn't connect let the modeler know

        @param connector: connector associated with this failure
        @type connector: object
        @param reason: failure object
        @type reason: object
        """
        from Products.ZenUtils.Utils import unused
        unused(connector)
        message= reason.getErrorMessage()
        log.error( message )
        sendEvent( self, device=self.hostname, message=message )
        self.clientFinished()


    def loseConnection(self):
        """
        Called when the connection gets closed.
        """
        log.debug( "Connection closed" )
        #self.connection.loseConnection()



def main():
    """
    Test harness main()

    Usage:

    python SshClient.py hostname[:port] comand [command]

    Each command must be enclosed in quotes (") to be interpreted
    properly as a complete unit.
    """
    import socket
    from itertools import chain
    import pprint

    logging.basicConfig()

    parser = CollectorClient.buildOptions()
    options = CollectorClient.parseOptions(parser,22)
    log.setLevel(options.logseverity)

    client = SshClient(options.hostname,
                       socket.gethostbyname(options.hostname),
                       options.port,
                       options=options)

    # Rather than getting info from zenhub, just pass our
    # commands in
    client.getCommands= lambda: chain( options.commands )

    client.run()

    client.clientFinished= reactor.stop
    client._commands.append( options.commands )
    reactor.run()

    pprint.pprint(client.getResults())


if __name__ == '__main__':
    main()
