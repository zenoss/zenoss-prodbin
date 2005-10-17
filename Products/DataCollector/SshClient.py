#################################################################
#
#   Copyright (c) 2003 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""SshClient

SshClient runs commands on a remote box using ssh 
and returns their results

$Id: SshClient.py,v 1.5 2004/04/05 02:05:30 edahl Exp $"""

__version__ = "$Revision: 1.5 $"[11:-2]

import os, getpass

from twisted.conch.ssh import transport, userauth, connection
from twisted.conch.ssh import common, keys, channel
from twisted.internet import defer, reactor

from Exceptions import *
from ObjectMap import ObjectMap

import CollectorClient

def check(hostname, timeout=2):
    "check to see if a device supports ssh"
    from telnetlib import Telnet
    import socket
    try:
        tn = Telnet(hostname, 22)
        index, match, data = tn.expect(['SSH-1.99', 'SSH-2.0',], timeout)
        tn.close()
        if index == 0: return 1
        return index
    except socket.error:
        return 0
    


class SshClientTransport(transport.SSHClientTransport):

    def verifyHostKey(self, hostKey, fingerprint):
        self.log = self.factory.log
        #blowing off host key right now, should store and check
        self.log.debug('%s host key: %s' % (self.factory.hostname, fingerprint))
        return defer.succeed(1) 

    def connectionSecure(self): 
        sshconn = SshConnection(self.factory, self.log)
        self.factory.connection = sshconn
        sshauth = SshUserAuth(self.factory.username, 
                                sshconn, self.factory, self.log)
        self.requestService(sshauth)
            
                
class SshUserAuth(userauth.SSHUserAuthClient):
    def __init__(self, user, instance, factory, log=None):
        userauth.SSHUserAuthClient.__init__(self, user, instance)
        self.user = user
        self.factory = factory
        self.log = log

    def getPassword(self):
        if not self.factory.password:
            self.log.debug("ssh asking for password")
            if not self.factory.loginTries:
                if __name__ == "__main__": reactor.stop() #FIXME
                raise LoginFailed, "login to %s with username %s failed" % (
                                self.factory.hostname, self.factory.username)
            else:
                self.factory.loginTries -= 1
            return defer.succeed(getpass.getpass(
                "%s@%s's password: " % (self.user, self.factory.hostname)))
        else:
            return defer.succeed(self.factory.password)

    def getPublicKey(self):
        self.log.debug("getting public key")
        path = os.path.expanduser('~/.ssh/id_dsa') 
        # this works with rsa too
        # just change the name here and in getPrivateKey
        if not os.path.exists(path) or hasattr(self, 'lastPublicKey'):
            # the file doesn't exist, or we've tried a public key
            return
        return keys.getPublicKeyString(path+'.pub')

    def getPrivateKey(self):
        self.log.debug("getting private key")
        path = os.path.expanduser('~/.ssh/id_dsa')
        return defer.succeed(keys.getPrivateKeyObject(path))


class SshConnection(connection.SSHConnection):

    def __init__(self, factory, log=None):
        connection.SSHConnection.__init__(self)
        self.factory = factory
        self.log = log


    def serviceStarted(self):
        """run commands that are in the command queue"""
        self.log.info("connected to device %s" % self.factory.hostname)
        for cmd in self.factory.getCommands():
            self.addCommand(cmd)


    def addCommand(self, cmd):
        """open a new command channel for each command in queue"""
        ch = CommandChannel(cmd, conn=self, log=self.log)
        self.openChannel(ch)


class CommandChannel(channel.SSHChannel):
    name = 'session'

    def __init__(self, command, conn=None, log=None):
        channel.SSHChannel.__init__(self, conn=conn)
        self.command = command
        self.log = log
        
    def openFailed(self, reason):
        self.log.warn('open of %s failed: %s' % (self.command, reason))

    def channelOpen(self, ignoredData):
        self.log.debug('opening command channel for %s' % self.command)
        self.data = ''
        d = self.conn.sendRequest(self, 'exec', 
            common.NS(self.command), wantReply = 1)

    def dataReceived(self, data):
        self.data += data

    def closed(self):
        self.log.debug('command %s data: %s' % (self.command, repr(self.data)))
        self.conn.factory.addResult(self.command, self.data)
        self.loseConnection()
        if self.conn.factory.commandsFinished():
            self.conn.factory.clientFinished()


class SshClient(CollectorClient.CollectorClient):

    def __init__(self, hostname, port=22, commands=[], options=None, 
                    device=None, datacollector=None, log=None):
        CollectorClient.CollectorClient.__init__(self, hostname, port, 
                           commands, options, device, datacollector, log)
        self.protocol = SshClientTransport
        self.connection = None
        if check(self.hostname):
            reactor.connectTCP(self.hostname, self.port, self)
        else:
            raise NoServerFound, \
                "Ssh server not found on %s port %s" % (
                                self.hostname, self.port)

    def addCommand(self, commands):
        """add command to queue and open a command channel for a command"""
        CollectorClient.CollectorClient.addCommand(self, commands)
        if type(commands) == type(''): commands = (commands,)
        for cmd in commands:
            self.connection.addCommand(cmd)
   
    def loseConnection(self):
        pass
        #self.connection.loseConnection()


def main():
    parser = CollectorClient.buildOptions()
    options = CollectorClient.parseOptions(parser,22)
    client = SshClient(options.hostname, options.port, 
                commands=options.commands, options=options)
    while 1:
        reactor.iterate()
        if client.commandsFinished():
            break
    import pprint
    pprint.pprint(client.getResults())

if __name__ == '__main__':
    main()
