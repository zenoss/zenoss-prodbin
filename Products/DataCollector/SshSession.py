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
#!/usr/bin/env python
from twisted.conch.ssh import transport, userauth, connection, common, keys, channel
from twisted.internet import defer, protocol, reactor
from twisted.python import log
import struct, sys, getpass, os


from Exceptions import NoValidConnection, LoginFailed, CommandTimeout

class SshSession:

    def __init__(self, searchPath=[], existenceCheck='test -f %s', 
                    options=None, context=None, log=None):

        self.searchPath = searchPath
        self.existenceCheck = existenceCheck

        if log:
            self.log = log
        else:
            logging.basicConfig()
            self.log = logging.getLogger(self.__class__.__name__)
            if options: self.log.setLevel(options.logseverity)


    def check(self, hostname, timeout=1):
        "check to see if a device supports ssh"
        from telnetlib import Telnet
        import socket
        try:
            tn = Telnet(hostname, 22)
            index, match, data = tn.expect(['SSH',], timeout)
            tn.close()
            if index == 0: return 1
        except socket.error:
            return 0
    
    def connect(self, hostname, username=None, password=None):
        "login to a machine using ssh"
        pass


    def execute(self, command, timeout=None):
        """run a command that will be found by our path if it has been passed
        and return its output"""
        fullcommand  = self.findFullCommand(command)
        if fullcommand:
            return self._execute(fullcommand, timeout)
        else:
            raise CommandNotFound, "unable to find command '%s'" % command


    def _execute(self, command, timeout=None):
        "run a command using the shell path and return its output"
        pass


    def disconnect(self):
        "close the telnet session"
        pass  


    def findFullCommand(self, command):
        "look through the path list to find the full path to this command"
        if not self.searchPath: return command
        if type(self.searchPath) == type(''):
            self.searchPath = self.searchPath.split(":")
        basecmd = command.split()[0] #remove args
        for path in self.searchPath:
            fullcmd = os.path.join(path, basecmd)
            self._execute(self.existenceCheck % fullcmd)
            if int(self._execute("echo $?")) == 0:
                return os.path.join(path, command)
        self.log.warn('unable to find command %s in search path %s' % 
                                (self.searchPath, command))





class SimpleTransport(transport.SSHClientTransport):
    def verifyHostKey(self, hostKey, fingerprint):
        print 'host key fingerprint: %s' % fingerprint
        return defer.succeed(1) 

    def connectionSecure(self):
        self.requestService(SimpleUserAuth(USER,SimpleConnection()))
            
                

class SimpleUserAuth(userauth.SSHUserAuthClient):
    def getPassword(self):
        return defer.succeed(
            getpass.getpass("%s@%s's password: " % (USER, HOST)))

    def getPublicKey(self):
        log.debug('Getting Public Key from %s' % self.factory.keyPath)
        path = os.path.expanduser(self.factory.keyPath)
        # this works with rsa too
        # just change the name here and in getPrivateKey
        if not os.path.exists(path) or hasattr(self, 'lastPublicKey'):
            # the file doesn't exist, or we've tried a public key
            return
        return keys.getPublicKeyString(path+'.pub')

    def getPrivateKey(self):
        log.debug('Getting Private Key from %s' % self.factory.keyPath)
        path = os.path.expanduser(self.factory.keyPath)
        return defer.succeed(keys.getPrivateKeyObject(path))


class SimpleConnection(connection.SSHConnection):
    def serviceStarted(self):
        for cmd in commands:
            ch = CommandChannel(2**16, 2**15, self)
            ch.command = cmd
            self.openChannel(ch)


class FindCmdChannel(channel.SSHChannel):
    
    def openFailed(self, reason):
        print 'find command %s in path %s failed: %s' % (command, path, reason)

    def channelOpen(self, ignoredData):
        self.conn.sendRequest(self, 'exec', common.NS(''))

    def request_exit_status(self, data):
        status = struct.unpack('>L', data)[0]
        if not status:
            fpcommand = 0
        self.loseConnection()




class CommandChannel(channel.SSHChannel):
    name = 'session'

    def openFailed(self, reason):
        self.log.warn('open of %s failed: %s' % (self.command, reason))

    def channelOpen(self, ignoredData):
        #self.command = '/bin/netstat -an'
        self.data = ''
        d = self.conn.sendRequest(self, 'exec', 
            common.NS(self.command), wantReply = 1)
    #    d.addCallback(self._cbRequest)

    #def _cbRequest(self, ignored):
    #    self.conn.sendEOF(self)

    def dataReceived(self, data):
        self.data += data

    def closed(self):
        #print 'command %s data: %s' % (self.command, repr(self.data))
        self.loseConnection()
        results.append(self.data)
        if len(results) == len(commands):
            reactor.stop()


#import pprint
#for HOST in hosts:
#    protocol.ClientCreator(reactor, SimpleTransport).connectTCP(HOST, 22)
#    reactor.run()
#    print HOST
#    pprint.pprint(results)
#    results = []
