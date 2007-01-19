#################################################################
#
#   Copyright (c) 2003 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""SshClient

SshClient runs commands on a remote box using ssh 
and returns their results

$Id: SshClient.py,v 1.5 2004/04/05 02:05:30 edahl Exp $"""

__version__ = "$Revision: 1.5 $"[11:-2]

import os, getpass
import logging
log = logging.getLogger("zen.SshClient")

import Globals

from twisted.conch.ssh import transport, userauth, connection
from twisted.conch.ssh import common, keys, channel
from twisted.internet import defer, reactor

from Exceptions import *

import CollectorClient

class SshClientTransport(transport.SSHClientTransport):

    def verifyHostKey(self, hostKey, fingerprint):
        #blowing off host key right now, should store and check
        log.debug('%s host key: %s' % (self.factory.hostname, fingerprint))
        return defer.succeed(1)

    def connectionMade(self):
        self.factory.transport = self.transport
        transport.SSHClientTransport.connectionMade(self)

    def connectionSecure(self): 
        sshconn = SshConnection(self.factory)
        self.factory.connection = sshconn
        sshauth = SshUserAuth(self.factory.username, sshconn, self.factory)
        self.requestService(sshauth)

                
class SshUserAuth(userauth.SSHUserAuthClient):
    lastPublicKey = False
    def __init__(self, user, instance, factory):
        userauth.SSHUserAuthClient.__init__(self, user, instance)
        self.user = user
        self.factory = factory

    def getPassword(self):
        if not self.factory.password or self.factory.loginTries <= 0:
            self.factory.clientFinished()
            return
        else:
            self.factory.loginTries -= 1
            return defer.succeed(self.factory.password)

    def getPublicKey(self):
        log.debug('Getting Public Key from %s' % self.factory.keyPath)
        keyPath = os.path.expanduser(self.factory.keyPath)
        # this works with rsa too
        # just change the name here and in getPrivateKey
        path = None
        if os.path.exists(keyPath):
            path = keyPath
        if not path or self.lastPublicKey:
            # the file doesn't exist, or we've tried a public key
            return
        return keys.getPublicKeyString(path+'.pub')

    def getPrivateKey(self):
        log.debug('Getting Private Key from %s' % self.factory.keyPath)
        keyPath = os.path.expanduser(self.factory.keyPath)
        path = None
        if os.path.exists(keyPath):
            path = keyPath
        return defer.succeed(keys.getPrivateKeyObject(path))

class SshConnection(connection.SSHConnection):

    def __init__(self, factory):
        log.debug("creating new ssh connection")
        connection.SSHConnection.__init__(self)
        self.factory = factory


    def serviceStarted(self):
        """run commands that are in the command queue"""
        log.info("connected to device %s" % self.factory.hostname)
        for cmd in self.factory.getCommands():
            self.addCommand(cmd)


    def addCommand(self, cmd):
        """open a new command channel for each command in queue"""
        ch = CommandChannel(cmd, conn=self)
        self.openChannel(ch)

    def channelClosed(self, channel):
        # grr.. patch SSH inherited method to deal with partially
        # configured channels
        self.localToRemoteChannel[channel.id] = None
        self.channelsToRemoteChannel[channel] = None
        connection.SSHConnection.channelClosed(self, channel)


class CommandChannel(channel.SSHChannel):
    name = 'session'

    def __init__(self, command, conn=None):
        channel.SSHChannel.__init__(self, conn=conn)
        self.command = command
        self.exitCode = None
        
    def openFailed(self, reason):
        log.warn('open of %s failed: %s' % (self.command, reason))

    def channelOpen(self, ignoredData):
        log.debug('opening command channel for %s' % self.command)
        self.data = ''
        d = self.conn.sendRequest(self, 'exec', common.NS(self.command),
                                  wantReply = 1)

    def request_exit_status(self, data):
        import struct
        self.exitCode = struct.unpack('>L', data)[0]

    def dataReceived(self, data):
        self.data += data

    def closed(self):
        log.debug('command %s data: %s' % (self.command, repr(self.data)))
        self.conn.factory.addResult(self.command, self.data, self.exitCode)
        self.loseConnection()
        if self.conn.factory.commandsFinished():
            self.conn.factory.clientFinished()


class SshClient(CollectorClient.CollectorClient):

    def __init__(self, hostname, ip, port=22, commands=[], options=None, 
                    device=None, datacollector=None):
        CollectorClient.CollectorClient.__init__(self, hostname, ip, port, 
                           commands, options, device, datacollector)
        self.protocol = SshClientTransport
        self.connection = None
        self.transport = None


    def run(self):
        """Start ssh collection.
        """
        reactor.connectTCP(self.ip, self.port, self, self.loginTimeout)


    def addCommand(self, commands):
        """add command to queue and open a command channel for a command"""
        CollectorClient.CollectorClient.addCommand(self, commands)
        if type(commands) == type(''): commands = (commands,)
        if self.connection:
            for cmd in commands:
                self.connection.addCommand(cmd)
   
    def loseConnection(self):
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
