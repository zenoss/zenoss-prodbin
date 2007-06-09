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

__doc__="""TelnetSession

TelnetSession is used by TelnetSession to issue commands to a machine
and return their output over the telnet protocol.

Device Tree Parameters are:

zTelnetLoginTries - number of times to try login default: 1
zTelnetLoginTimeout - timeout for expect statements during login default: 2
zTelnetPromptTimeout - pause used during prompt discovery default: 0.2
zTelnetCommandTimeout - default timeout when executing a command default: 5
zTelnetLoginRegex - regex to match the login prompt default: 'ogin:.$'
zTelnetPasswordRegex - regext to match the password prompt default: 'assword:.$'

Other Parameters that are used by both TelnetSession and SshTransport:
zCommandPathList - list of path to check for a command
zCommandExistanceCheck - shell command issued to look for executible
                        must echo succ if executible is found
                        default: test -f executible

$Id: TelnetClient.py,v 1.15 2004/04/05 02:05:30 edahl Exp $"""

__version__ = "$Revision: 1.15 $"[11:-2]

import Globals

#FIXME take away except when we are totally migrated
try:
    from twisted.conch import telnet
except:
    from twisted.protocols import telnet

from twisted.internet import protocol, reactor

import re
import logging
log = logging.getLogger("zen.TelnetClient")

import CollectorClient
from Exceptions import *

defaultPromptTimeout = 10 
defaultCommandTimeout = 20
defaultLoginRegex = 'ogin:.$'
defaultPasswordRegex = 'assword:'
defaultEnable = False
defaultTermLength = False


responceMap = ("WILL", "WONT", "DO", "DONT")

def check(hostname):
    "check to see if a device supports telnet"
    from telnetlib import Telnet
    import socket
    try:
        tn = Telnet(hostname)
        tn.close()
        return 1
    except socket.error:
        return 0


class TelnetClientProtocol(telnet.Telnet):
    mode = 'Login'

    timeout = 0
    timeoutID = None
    p1 = ""
    p2 = ""
    commandPrompt = ""
    command = ''
    enabled = -1 
    scCallLater = None
    bytes = ''
    lastwrite = ''
    result = ''
    buffer = ""

    def connectionMade(self):
        self.factory.myprotocol = self #bogus hack
        self.hostname = self.factory.hostname
        log.info("connected to device %s" % self.hostname)
        self.startTimeout(self.factory.loginTimeout, self.loginTimeout)
        self.protocol = telnet.TelnetProtocol()

    # the following functions turn off all telnet options
    def iac_DO(self, feature):
        log.debug("received telnet DO feature %s" % ord(feature))
        if ord(feature) == 1: 
            self._iac_responce(telnet.WILL, feature)
        else:
            self._iac_responce(telnet.WONT, feature)

    def iac_DONT(self, feature):
        log.debug("received telnet DONT feature %s" % ord(feature))
        self._iac_responce(telnet.WONT, feature)

    def iac_WILL(self, feature):
        log.debug("received telnet WILL feature %s" % ord(feature))
        self._iac_responce(telnet.DONT, feature)

    def iac_WONT(self, feature):
        log.debug("received telnet WONT feature %s" % ord(feature))
        self._iac_responce(telnet.DONT, feature)

    def _iac_responce(self, action, feature):
        log.debug("sending telnet action %s feature %s" % 
                            (responceMap[ord(action)-251], ord(feature)))
        self.write(telnet.IAC+action+feature)


    def write(self, data):
        "save the last bit of data that we wrote"
        self.lastwrite = data
        self.transport.write(data)

    def processChunk(self, chunk):
        self.buffer = self.buffer + chunk
        regex = None
        if self.factory.modeRegex.has_key(self.mode):
            regex = self.factory.modeRegex[self.mode] 
        log.debug("mode '%s' regex = %s" % (self.mode, regex))
        log.debug("chunk received = '%s'" % chunk)
        if regex and re.search(regex, chunk):
            self.processLine(self.buffer)
            self.buffer = ""
        
    def processLine(self, line):
        """I call a method that looks like 'telnet_*' where '*' is filled
        in by the current mode. telnet_* methods should return a string which
        will become the new mode."""
        line = re.sub("\r\n|\r", "\n", line) #convert \r\n to \n
        #if server is echoing take it out
        if self.lastwrite.startswith(line):
            self.lastwrite = self.lastwrite[len(line):]
            line = ''
        elif line.find(self.lastwrite) == 0: 
            line = line[len(self.lastwrite):]
        log.debug("mode = %s", self.mode)
        self.mode = getattr(self, "telnet_"+self.mode)(line)

    def dataReceived(self, data):
        telnet.Telnet.dataReceived(self, data)
        log.debug('line %r', self.bytes)
        if self.bytes:
            self.processLine(self.bytes)
        self.bytes = ''
            
    def applicationDataReceived(self, bytes):
        self.bytes += bytes


    def startTimeout(self, timeout=1, timeoutfunc=None):
        self.cancelTimeout() 
        if timeoutfunc is None: timeoutfunc = self.defaultTimeout
        self.timeoutID = reactor.callLater(timeout, timeoutfunc) 


    def cancelTimeout(self):
        if self.timeoutID: self.timeoutID.cancel()
        self.timeoutID = None


    def defaultTimeout(self):
        self.transport.loseConnection()
        if self.factory.commandsFinished():
            self.factory.clientFinished()
        regex = self.factory.modeRegex.get(self.mode, "")
        log.warn("dropping connection to %s: "
            "state '%s' timeout %.1f seconds regex '%s' buffer '%s'",
            self.factory.hostname, self.mode, self.timeout,regex,self.buffer)

                                                    

    def loginTimeout(self, loginTries=0):
        if loginTries == 0:
            loginTries = self.factory.loginTries
        elif loginTries == 1:
            self.transport.loseConnection()
            self.factory.clientFinished()
            log.warn("login to device %s failed" % self.hostname)
            return "Done"
        else:
            self.factory.loginTries -= 1
            return "Login"
   

    def telnet_Login(self, data):
        "Called when login prompt is received"
        log.debug('Search finds: %r', re.search(self.factory.loginRegex, data))
        if not re.search(self.factory.loginRegex, data): # login failed
            return 'Login'
        log.debug("login tries=%s" % self.factory.loginTries)
        if not self.factory.loginTries:
            self.transport.loseConnection()
            log.warn("login to %s with username %s failed" % (
                                self.factory.hostname, self.factory.username))
        else:
            self.factory.loginTries -= 1
        log.debug("sending username %s" % self.factory.username)
        self.write(self.factory.username + '\n')
        return 'Password'


    def telnet_Password(self, data):
        "Called when the password prompt is received"
        if not re.search(self.factory.passwordRegex, data): # look for pw prompt
            return 'Password'
        log.debug("sending password %s" % self.factory.password)
        self.write(self.factory.password + '\n')
        self.startTimeout(self.factory.promptTimeout)
        return 'FindPrompt'


    def telnet_Enable(self, data):
        "change to enable mode on cisco"
        self.write('enable\n')
        self.startTimeout(self.factory.loginTimeout, self.loginTimeout)
        return "Password"


    def telnet_FindPrompt(self, data):
        "Called after login to figure out the command prompt"
        if not data.strip(): return 'FindPrompt'
        if re.search(self.factory.loginRegex, data): # login failed
            return self.telnet_Login(data)
        self.p1 = data
        if self.p1 == self.p2:
            self.cancelTimeout() # promptTimeout
            self.commandPrompt = self.p1
            log.debug("found command prompt '%s'" % self.p1)
            self.factory.modeRegex['Command'] = re.escape(self.p1) + "$"
            self.factory.modeRegex['SendCommand'] = re.escape(self.p1) + "$"
            if self.factory.enable:
                self.factory.enable = False
                return self.telnet_Enable("")
            else:
                self.scCallLater = reactor.callLater(1.0, 
                    self.telnet_SendCommand, "")
                return "ClearPromptData"
        self.p2 = self.p1
        self.p1 = ""
        log.debug("sending \\n")
        reactor.callLater(.1, self.write, "\n")
        return 'FindPrompt' 

    def telnet_ClearPromptData(self, data):
        if self.scCallLater: self.scCallLater.cancel()
        self.scCallLater = reactor.callLater(1.0, self.telnet_SendCommand, "")
        return "ClearPromptData"

    def telnet_SendCommand(self, data):
        "Get a command of the command stack and send it"
        if self.scCallLater and self.scCallLater.active(): 
            self.scCallLater.cancel()
        log.debug("sending command '%s'" % self.curCommand())
        self.write(self.curCommand() + '\n')
        self.startTimeout(self.factory.commandTimeout)
        self.mode = 'Command'
        return 'Command'
        

    def telnet_Command(self, data):
        """process the data from a sent command
        if there are no more commands move to final state"""
        self.result += data
        if not self.result.endswith(self.commandPrompt):
            log.debug("prompt '%s' not found", self.commandPrompt)
            log.debug("line ends wth '%s'", data[-5:])
            return 'Command'
        self.cancelTimeout()
        data, self.result = self.result, ''
        log.debug("command = %s" % self.curCommand())
        log.debug("data=%s" % data)
        self.factory.addResult(self.curCommand(), data[0:-len(self.p1)], None)
        self.factory.cmdindex += 1
        if self.factory.commandsFinished():
            self.factory.clientFinished()
            if not self.factory.maintainConnection:
                self.transport.loseConnection()
            return 'Done'
        else:
            return self.telnet_SendCommand("")


    def curCommand(self):
        return self.factory._commands[self.factory.cmdindex]

    
class TelnetClient(CollectorClient.CollectorClient):
    
    def __init__(self, hostname, ip, port, commands=[], options=None, 
                    device=None, datacollector=None):
        CollectorClient.CollectorClient.__init__(self, hostname, ip, port, 
                            commands, options, device, datacollector)
        self.protocol = TelnetClientProtocol
        self.modeRegex = { 
                    'FindPrompt' : '.*',
                    'WasteTime' : '.*',
                    'Done' : '',
                    }
        self.promptPause = 1

        if options:
            defaultPromptTimeout = options.promptTimeout
            defaultCommandTimeout = options.commandTimeout
            defaultLoginRegex = options.loginRegex
            defaultPasswordRegex = options.passwordRegex
            defaultEnable = options.enable
            defaultTermLength = options.termlen

        if device: # if we are in zope look for parameters in aq path
            self.promptTimeout = getattr(device, 
                        'zTelnetPromptTimeout', defaultPromptTimeout)
            self.loginRegex = getattr(device, 
                        'zTelnetLoginRegex', defaultLoginRegex)
            self.passwordRegex = getattr(device, 
                        'zTelnetPasswordRegex', defaultPasswordRegex)
            self.enable = getattr(device, 
                        'zTelnetEnable', defaultEnable)
            self.termlen = getattr(device, 
                        'zTelnetTermLength', defaultTermLength)
        else:
            self.promptTimeout = defaultPromptTimeout
            self.loginRegex = defaultLoginRegex
            self.passwordRegex = defaultPasswordRegex
            self.enable = defaultEnable
            self.termlen = defaultTermLength

        self.modeRegex['Login'] = self.loginRegex
        self.modeRegex['Password'] = self.passwordRegex


    def run(self):
        """Start telnet collection.
        """
        if self.termlen:
            self._commands.insert(0, "terminal length 0")
        reactor.connectTCP(self.ip, self.port, self)


    def Command(self, commands):
        """add new commands to be run reset cmdindex to 0"""
        CollectorClient.CollectorClient.addCommand(self, commands)
        if self.myprotocol.mode != "Command": 
            self.myprotocol.telnet_SendCommand("")


    def clientConnectionFailed(self, connector, reason):
        """if we don't connect let the modeler know"""
        log.warn(reason.getErrorMessage())
        self.clientFinished()
       

    def clientFinished(self):
        CollectorClient.CollectorClient.clientFinished(self)
        if __name__ == "__main__":
            reactor.stop()


def buildOptions(parser=None, usage=None):
    parser = CollectorClient.buildOptions(parser,usage)
    parser.add_option('-r', '--promptTimeout',
                dest='promptTimeout',
                type = 'float',
                default = defaultPromptTimeout,
                help='timeout when discovering prompt')
    parser.add_option('-x', '--loginRegex',
                dest='loginRegex',
                default = defaultLoginRegex,
                help='regex that will find the login prompt')
    parser.add_option('-w', '--passwordRegex',
                dest='passwordRegex',
                default = defaultPasswordRegex,
                help='regex that will find the password prompt')
    parser.add_option('--enable',
                dest='enable', action='store_true', default=False,
                help='enter enable mode on a cisco device')
    parser.add_option('--termlen',
                dest='termlen', action='store_true', default=False,
                help='enter send terminal length 0 on a cisco device')
    return parser


def main():
    import socket
    import getpass
    parser = buildOptions()
    options = CollectorClient.parseOptions(parser, 23)
    if not options.password:
        options.password = getpass.getpass("%s@%s's password: " % 
                        (options.username, options.hostname))
    logging.basicConfig(level=10)
    commands = [("test", c) for c in options.commands]
    client = TelnetClient(options.hostname,
                          socket.gethostbyname(options.hostname),
                          options.port,
                          commands=commands, options=options)
    client.run()
    def stop():
        if client.commandsFinished():
            reactor.stop()
        else:
            reactor.callLater(1, stop)
    stop()
    reactor.run()
    import pprint
    pprint.pprint(client.getResults())

if __name__ == '__main__':
    main()
