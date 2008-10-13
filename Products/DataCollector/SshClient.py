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
from twisted.python import failure
from Products.ZenEvents import Event

from Exceptions import *

import CollectorClient

# NB: Most messages returned back from Twisted are Unicode.
#     Expect to use str() to convert to ASCII before dumping out. :)


def sendEvent( self, message="", device='', severity=Event.Error ):
    """Shortcut version of sendEvent()
    """

    # Parse out the daemon's name
    component= os.path.basename( sys.argv[0] ).replace( '.py', '' )

    # ... and the device's name (as known by Zenoss)
    if device == '':
       try:
           device= self.factory.hostname
       except:
           try:
               device= self.conn.factory.hostname
           except:
               log.exception( "Couldn't get the remote device's hostname" )

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
        self.factory.datacollector.sendEvent( error_event )
    except:
        try:
           self.datacollector.sendEvent( error_event )
        except:
           try:
               self.conn.factory.datacollector.sendEvent( error_event )
           except:
               log.exception( "Unable to send event for %s" % error_event )



class SshClientError( Exception ):
    """
    Exception class
    """



class SshClientTransport(transport.SSHClientTransport):
    """Base client class for constructing Twisted Conch services.
    This class is *only* responsible for connecting to the SSH
    service on the device, and ensuring that *host* keys are sane.
    """

    def verifyHostKey(self, hostKey, fingerprint):
        """Module to verify the host's SSH key against the stored fingerprint we have
        from the last time that we communicated with the host.

        NB: currently does not verify this information but simply trusts every host key
        """

        #blowing off host key right now, should store and check
        from Products.ZenUtils.Utils import unused
        unused(hostKey)
        log.debug('%s host key: %s' % (self.factory.hostname, fingerprint))
        return defer.succeed(1)


    def connectionMade(self):
        """Called after the connection has been made.
        Used to set up private instance variables.
        """
        self.factory.transport = self.transport
        transport.SSHClientTransport.connectionMade(self)


    def receiveError( self, reasonCode, description ):
        """Called when a disconnect error message was received from the device.
        """
        message= 'SSH error from remote device (code %d): %s\n' % \
                 ( reasonCode, str( description ) )
        sendEvent( self, message=message )
        transport.SSHClientTransport.receiveError(self, reasonCode, description )


    def receiveUnimplemented( self, seqnum ):
        """Called when an unimplemented packet message was received from the device.
        """
        message= "Got 'unimplemented' SSH message, seqnum= %d" % seqnum
        sendEvent( self, message=message )
        transport.SSHClientTransport.receiveUnimplemented(self, seqnum)


    def receiveDebug( self, alwaysDisplay, message, lang ):
        """Called when a debug message was received from the device.
        """

        message= "Debug message from remote device (%s): %s" % ( str(lang), str(message) )
        sendEvent( self, message=message, severity=Event.Debug )

        transport.SSHClientTransport.receiveDebug(self, alwaysDisplay, message, lang )


    def connectionSecure(self):
        """This is called after the connection is set up and other services can be run.
        This function starts the SshUserAuth client (ie the Connection client).
        """

        sshconn = SshConnection(self.factory)
        sshauth = SshUserAuth(self.factory.username, sshconn, self.factory)
        self.requestService(sshauth)



class SshUserAuth(userauth.SSHUserAuthClient):
    """Class to gather credentials for use with our SSH connection,
       and use them to authenticate against the remote device.
    """

    def __init__(self, user, instance, factory):
        """If no username is supplied, defaults to the os.getlogin() return (ie zenoss)
        """

        user = str(user)                # damn unicode
        if user == '':
            user = os.getlogin()
        log.debug('attempting to authenticate using username: %s' % user)
        userauth.SSHUserAuthClient.__init__(self, user, instance)
        self.user = user
        self.factory = factory
        self.first_attempt= True  #  workaround for 'extra' auth failure


    def getPassword(self, unused=None):
        """Return a deferred object of success if there's a password and
        we haven't gone past the number of retry attempts.
        Otherwise return fail (ie password authentication failure)
        """

        if not self.factory.password:
            message= "SshUserAuth: no password able to be extracted"
            log.error( message )
            sendEvent( self, message=message )
            self.factory.clientFinished()
            return defer.fail( SshClientError( message ) )

        elif self.factory.loginTries <= 0:
            message= "SSH connection aborted after maximum login attempts."
            log.error( message )
            sendEvent( self, message=message )
            self.factory.clientFinished()
            return defer.fail( SshClientError( message ) )

        else:
            self.factory.loginTries -= 1
            return defer.succeed(self.factory.password)


    def getPublicKey(self):
        """Return the SSH public key (using the zProperty zKeyPath) or None
        """

        log.debug('Getting Public Key from %s' % self.factory.keyPath)
        keyPath = os.path.expanduser( self.factory.keyPath )
        log.debug('Expanded key path from %s to %s' % ( self.factory.keyPath, keyPath))
        path = None
        if os.path.exists(keyPath):
            path = keyPath

        else:
            log.debug( "Public key path %s doesn't exist" % keyPath )
            return

        return keys.getPublicKeyString( path + '.pub' )


    def ssh_USERAUTH_FAILURE( self, packet):
        """Called when the SSH session can't authenticate.
           Note that Twisted seems to attempt to authenticate
           once with unknown stuff before trying the user's
           credentials.
        """
        if not self.first_attempt:
            message= "SSH login to %s with username %s failed" % \
                     ( self.factory.hostname, self.user )
            log.error( message )
            sendEvent( self, message=message )

        self.first_attempt= False
        userauth.SSHUserAuthClient.ssh_USERAUTH_FAILURE( self, packet )


    def getPrivateKey(self):
        """Return a deferred with the private key (using the zProperty zKeyPath)
        """

        log.debug('Getting Private Key from %s' % self.factory.keyPath)
        keyPath = os.path.expanduser(self.factory.keyPath)
        log.debug('Expanded key path from %s to %s' % ( self.factory.keyPath, keyPath))
        path = None
        if os.path.exists(keyPath):
            path = keyPath
        else:
            log.debug( "Private key path %s doesn't exist" % keyPath )

        return defer.succeed(keys.getPrivateKeyObject(path,
                passphrase=self.factory.password))



class SshConnection(connection.SSHConnection):
    """Wrapper class that starts channels on top of connections.
    """

    def __init__(self, factory):
        """Initializer
        """
        log.debug( "creating new SSH connection..." )
        connection.SSHConnection.__init__(self)
        self.factory = factory


    def ssh_CHANNEL_FAILURE( self, packet):
        """Called when the SSH session can't authenticate
        """
        message= "CHANNEL_FAILURE: Authentication failure"
        log.error( message )
        sendEvent( self, message=message )
        connection.SSHConnection.ssh_CHANNEL_FAILURE( self, packet )


    def ssh_CHANNEL_OPEN_FAILURE( self, packet):
        """Called when the SSH session can't authenticate
        """
        message= "CHANNEL_OPEN_FAILURE: Authentication failure"
        log.error( message )
        sendEvent( self, message=message )
        connection.SSHConnection.ssh_CHANNEL_OPEN_FAILURE( self, packet )


    def ssh_REQUEST_FAILURE( self, packet):
        """Called when the SSH session can't authenticate
        """
        message= "REQUEST_FAILURE: Authentication failure"
        log.error( message )
        sendEvent( self, message=message )
        connection.SSHConnection.ssh_REQUEST_FAILURE( self, packet )


    def openFailed(self, reason):
        """Called when the connection open() fails.
        Usually this gets called after too many bad connection attempts,
        and the remote device gets upset with us.

        NB: reason.desc is the human-readable description of the failure
            reason.code is the SSH error code
         (see http://tools.ietf.org/html/rfc4250#section-4.2.2 for more details)
        """

        message= 'SSH connection to %s failed (error code %d): %s' % \
                 (self.command, reason.code, str(reason.desc) )
        log.error( message )
        sendEvent( self, message=message )
        connection.SSHConnection.openFailed( self, reason )


    def serviceStarted(self):
        """Called when the service is active on the transport
        """
        self.factory.serviceStarted(self)


    def addCommand(self, cmd):
        """Open a new command channel for each command in queue
        """
        ch = CommandChannel(cmd, conn=self)
        self.openChannel(ch)


    def channelClosed(self, channel):
        """Called when a channel is closed.
        REQUIRED function by Twisted.
        """
        # grr.. patch SSH inherited method to deal with partially
        # configured channels
        self.localToRemoteChannel[channel.id] = None
        self.channelsToRemoteChannel[channel] = None
        connection.SSHConnection.channelClosed(self, channel)



class CommandChannel(channel.SSHChannel):
    """The class that actually interfaces between Zenoss and the device.
    """

    name = 'session'

    def __init__(self, command, conn=None):
        """Initializer
        """
        channel.SSHChannel.__init__(self, conn=conn)
        self.command = command
        self.exitCode = None
        log.debug( "started the channel" )


    def openFailed(self, reason):
        """Called when the open fails.
        """
        message= 'Open of %s failed (error code %d): %s' % \
                 (self.command, reason.code, str( reason.desc ) )
        log.warn( message )
        sendEvent( self, message=message )
        channel.SSHChannel.openFailed( self, reason )


    def extReceived(self, dataType, data ):
        """Called when we receive extended data (usually standard error)
        """
        message= 'The command %s returned stderr data (%d) from the device: %s' \
                 % (self.command, dataType, data)
        log.warn( message )
        sendEvent( self, message=message )


    def channelOpen(self, unused):
        """Initializes the channel and send our command to the device.
        """

        log.debug('opening command channel for %s' % self.command)
        self.data = ''
        log.debug('running command remotely: exec %s' % self.command)

        #  Notes for sendRequest:
        # 'exec'      - execute the following command and exit
        # common.NS() - encodes the command as a length-prefixed string
        # wantReply   - reply to let us know the process has been started
        d = self.conn.sendRequest(self, 'exec', common.NS(self.command),
                                  wantReply = 1)
        return d


    def request_exit_status(self, data):
        """Gathers the exit code from the device
        """
        import struct
        self.exitCode = struct.unpack('>L', data)[0]


    def dataReceived(self, data):
        """Response stream from the device.  Can be called multiple times.
        """
        self.data += data


    def closed(self):
        """Cleanup for the channel, as both ends have closed the channel.
        """

        log.debug('command %s data: %s' % (self.command, repr(self.data)))
        self.conn.factory.addResult(self.command, self.data, self.exitCode)
        self.loseConnection()

        if self.conn.factory.commandsFinished():
            self.conn.factory.clientFinished()



class SshClient(CollectorClient.CollectorClient):
    """SSH Collector class to connect to a particular device
    """

    def __init__(self, hostname, ip, port=22, plugins=[], options=None,
                    device=None, datacollector=None):
        """Initializer
        """

        CollectorClient.CollectorClient.__init__(self, hostname, ip, port,
                           plugins, options, device, datacollector)
        self.hostname = hostname
        self.protocol = SshClientTransport
        self.connection = None
        self.transport = None


    def run(self):
        """Start SSH collection.
        """
        reactor.connectTCP(self.ip, self.port, self, self.loginTimeout)


    def serviceStarted(self, sshconn):
        """Run commands that are in the command queue
        """

        log.info("connected to device %s" % self.hostname)
        self.connection = sshconn
        for cmd in self.getCommands():
            sshconn.addCommand(cmd)


    def addCommand(self, commands):
        """Add a command or commands to queue and open a command
        channel for each command
        """

        CollectorClient.CollectorClient.addCommand(self, commands)
        if type(commands) == type(''):
            commands = (commands,)
        if self.connection:
            for cmd in commands:
                self.connection.addCommand(cmd)


    def clientConnectionFailed( self, connector, reason ):
        """If we didn't connect let the modeler know
        """
        from Products.ZenUtils.Utils import unused
        unused(connector)
        message= reason.getErrorMessage()
        log.error( message )
        sendEvent( self, device=self.hostname, message=message )
        self.clientFinished()


    def loseConnection(self):
        """Called when the connection gets closed.
        """
        pass
        #self.connection.loseConnection()



def main():
    import socket
    parser = CollectorClient.buildOptions()
    options = CollectorClient.parseOptions(parser,22)
    client = SshClient(options.hostname,
                       socket.gethostbyname(options.hostname),
                       options.port,
                commands=options.commands, options=options)
    def stop():
        if client.commandsFinished():
            reactor.stop()
        else:
            reactor.callLater(1, stop)
    stop()
    client.run()
    reactor.run()
    import pprint
    pprint.pprint(client.getResults())

if __name__ == '__main__':
    main()
