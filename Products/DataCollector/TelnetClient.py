#################################################################
#
#   Copyright (c) 2003 Zenoss, Inc. All rights reserved.
#
#################################################################

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
defaultEnableRegex = 'assword:'
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

    def connectionMade(self):
        self.factory.myprotocol = self #bogus hack
        self.hostname = self.factory.hostname
        log.info("connected to device %s" % self.hostname)
        self.setTimeout(self.factory.loginTimeout, self.loginTimeout)
        self.startTimeout()        

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
        telnet.Telnet.write(self, data)
       

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
        self.cancelTimeout()
        line = re.sub("\r\n|\r", "\n", line) #convert \r\n to \n
        #if server is echoing take it out
        if line.find(self.lastwrite) == 0: 
            line = line[len(self.lastwrite):]
        self.mode = getattr(self, "telnet_"+self.mode)(line)
        if not self.mode == 'Done': self.startTimeout()        


    def startTimeout(self):
        if self.timeout > 0:
            self.timeoutID = reactor.callLater(self.timeout, self.timeoutfunc) 

    def setTimeout(self, timeout, timeoutfunc=None):
        self.timeout = timeout
        if not timeoutfunc:
            self.timeoutfunc = self.defaultTimeout
        else:
            self.timeoutfunc = timeoutfunc

    def cancelTimeout(self):
        if self.timeoutID: self.timeoutID.cancel()
        self.timeoutID = None


    def defaultTimeout(self):
        self.transport.loseConnection()
        if self.factory.commandsFinished():
            self.factory.clientFinished()
        log.warn("dropping connection to %s: "
            "state '%s' timeout %.1f seconds regex '%s' buffer '%s'" % 
            (self.factory.hostname, self.mode, self.timeout, 
            self.factory.modeRegex[self.mode], self.buffer))
                                                    

    def loginTimeout(self):
        if self.factory.loginTries == 1:
            self.transport.loseConnection()
            self.factory.clientFinished()
            log.warn("login to device %s failed" % self.hostname)
            return "Done"
        else:
            self.factory.loginTries -= 1
            return "Login"
   

    def telnet_Login(self, data):
        "Called when login prompt is received"
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
        log.debug("sending password %s" % self.factory.password)
        self.write(self.factory.password + '\n')
        self.setTimeout(self.factory.promptTimeout)
        return 'FindPrompt'


    def telnet_Enable(self, data):
        "change to enable mode on cisco"
        self.write('enable\n')
        return "Password"


    def telnet_FindPrompt(self, data):
        "Called after login to figure out the command prompt"
        if not data.strip(): return 'FindPrompt'
        if re.search(self.factory.loginRegex, data): # login failed
            return self.telnet_Login(data)
        if self.enabled == 0:
            if data.find(self.commandPrompt) > -1:
                self.transport.loseConnection()
                log.warn("enable on %s failed" % self.factory.hostname)
            else:
                self.enabled += 1
        self.p1 = data
        if self.p1 == self.p2:
            self.commandPrompt = self.p1
            log.debug("found command prompt '%s'" % self.p1)
            self.factory.modeRegex['Command'] = re.escape(self.p1) + "$"
            self.factory.modeRegex['SendCommand'] = re.escape(self.p1) + "$"
            if self.factory.enable and self.enabled < 1:
                self.enabled += 1
                return self.telnet_Enable("")
            else:
                self.scCallLater = reactor.callLater(1.0, 
                                        self.telnet_SendCommand, "")
                return "SendCommand"
        self.p2 = self.p1
        self.p1 = ""
        log.debug("sending \\n")
        self.write("\n")
        return 'FindPrompt' 


    def telnet_SendCommand(self, data):
        "Get a command of the command stack and send it"
        if self.scCallLater and self.scCallLater.active(): 
            self.scCallLater.cancel()
        log.debug("sending command '%s'" % self.curCommand())
        self.write(self.curCommand() + '\n')
        self.setTimeout(self.factory.commandTimeout)
        self.mode = 'Command'
        return 'Command'
        

    def telnet_Command(self, data):
        """process the data from a sent command
        if there are now more commands move to final state"""
        log.debug("command = %s" % self.curCommand())
        log.debug("data=%s" % data)
        self.factory.addResult(self.curCommand(), data[0:-len(self.p1)])
        if self.factory.commandsFinished():
            self.factory.clientFinished()
            if not self.factory.maintainConnection:
                self.transport.loseConnection()
            return 'Done'
        else:
            self.factory.cmdindex += 1
            return self.telnet_SendCommand("")


    def curCommand(self):
        return self.factory.commands[self.factory.cmdindex]

    
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
            defaultEnableRegex = options.enableRegex
            defaultEnable = options.enable
            defaultTermLength = options.termlen

        if device: # if we are in zope look for parameters in aq path
            self.promptTimeout = getattr(device, 
                        'zTelnetPromptTimeout', defaultPromptTimeout)
            self.loginRegex = getattr(device, 
                        'zTelnetLoginRegex', defaultLoginRegex)
            self.passwordRegex = getattr(device, 
                        'zTelnetPasswordRegex', defaultPasswordRegex)
            self.enableRegex = getattr(device, 
                        'zTelnetEnableRegex', defaultEnableRegex)
            self.enable = getattr(device, 
                        'zTelnetEnable', defaultEnable)
            self.termlen = getattr(device, 
                        'zTelnetTermLength', defaultTermLength)
        else:
            self.promptTimeout = defaultPromptTimeout
            self.loginRegex = defaultLoginRegex
            self.passwordRegex = defaultPasswordRegex
            self.enableRegex = defaultEnableRegex
            self.enable = defaultEnable
            self.termlen = defaultTermLength

        self.modeRegex['Login'] = self.loginRegex
        self.modeRegex['Password'] = self.passwordRegex


    def run(self):
        """Start telnet collection.
        """
        if self.termlen:
            self.commands.insert(0, "terminal length 0")
        if check(self.ip):
            reactor.connectTCP(self.ip, self.port, self)
        else:
            raise NoServerFound, \
                "Telnet server not found on %s port %s" % (
                                self.hostname, self.port)



    def commandsFinished(self):
        """called by protocol to see if all commands have been run"""
        return len(self.commands) == self.cmdindex + 1


    def Command(self, commands):
        """add new commands to be run reset cmdindex to 0"""
        CollectorClient.CollectorClient.addCommand(self, commands)
        if self.myprotocol.mode != "Command": 
            self.myprotocol.telnet_SendCommand("")



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
    parser.add_option('--enablePause',
                dest='enablePause', type='float',
                #default = defaultEnablePause,
                help = 'time to wait before sending enable command')
    parser.add_option('--enableRegex',
                dest='enableRegex',
                default = defaultEnableRegex,
                help='regex that will find the enable password prompt')
    return parser


def main():
    import getpass
    parser = buildOptions()
    options = CollectorClient.parseOptions(parser, 23)
    if not options.password:
        options.password = getpass.getpass("%s@%s's password: " % 
                        (options.username, options.hostname))
    client = TelnetClient(options.hostname, options.port,
                    commands=options.commands, options=options)
    while 1:
        reactor.iterate()
        if client.commandsFinished():
            break
    import pprint
    pprint.pprint(client.getResults())

if __name__ == '__main__':
    main()
