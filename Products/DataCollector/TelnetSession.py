#################################################################
#
#   Copyright (c) 2003 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""TelnetSession

TelnetSession is used by TelnetSession to issue commands to a machine
and return their output over the telnet protocol.

Device Tree Parameters are:

zTelnetLoginTries - number of times to try login default: 1
zTelnetLoginTimeout - timeout for expect statements during login default: 2
zTelnetPromptPause - pause used during prompt discovery default: 0.2
zTelnetCommandTimeout - default timeout when executing a command default: 5
zTelnetLoginRegex - regex to match the login prompt default: 'ogin:.$'
zTelnetPasswordRegex - regext to match the password prompt default: 'assword:.$'
zTelnetSuccessRegexList - list of regex that match good login prompts
                            default: [ '\$.$', '\#.$' ]

Other Parameters that are used by both TelnetSession and SshTransport:
zCommandPathList - list of path to check for a command
zCommandExistanceCheck - shell command issued to look for executible
                        must echo succ if executible is found
                        default: test -f executible

$Id: TelnetSession.py,v 1.5 2004/02/14 19:11:00 edahl Exp $"""

__version__ = "$Revision: 1.5 $"[11:-2]

import time
import telnetlib
import re
import os.path

import logging

from Exceptions import NoValidConnection, LoginFailed, CommandTimeout


class TelnetSession:

    def __init__(self, searchPath=[], existanceCheck='test -f %s', 
                    options=None, context=None, log=None):

        self.searchPath = searchPath
        self.existanceCheck = existanceCheck

        defaultLoginTries = 1
        defaultLoginTimeout = 2
        defaultPromptPause = 0.2
        defaultCommandTimeout = 5
        defaultLoginRegex = 'ogin:.$'
        defaultPasswordRegex = 'assword:.$'
        defaultSuccessRegexList = [ '\$.$', '\#.$' ]

        if options and options.loginTries:
            defaultLoginTries = options.loginTries
    
        if options and options.loginTimeout:
            defaultLoginTimeout = options.loginTimeout
            
        if options and options.promptPause:
            defaultPromptPause = options.promptPause

        if options and options.commandTimeout:
            defaultCommandTimeout = options.commandTimeout
            
        if options and options.loginRegex:
            defaultLoginRegex = options.loginRegex

        if options and options.passwordRegex:
            defaultPasswordRegex = options.passwordRegex


        if context: # if we are in zope look for parameters in aq path
            self.loginTries = getattr(self, 
                        'zTelnetLoginTries', defaultLoginTries)
            self.loginTimeout = getattr(self, 
                        'zTelnetLoginTimeout', defaultLoginTimeout)
            self.promptPause = getattr(self, 
                        'zTelnetPromptPause', defaultPromptPause)
            self.commandTimeout = getattr(self, 
                        'zTelnetCommandTimeout', defaultCommandTimeout)
            self.loginRegex = getattr(self, 
                        'zTelnetLoginRegex', defaultLoginRegex)
            self.passwordRegex = getattr(self, 
                        'zTelnetPasswordRegex', defaultPasswordRegex)
            self.successRegexList = getattr(self, 
                        'zTelnetSuccessRegexList', defaultSuccessRegexList)
        else:
            self.loginTries = defaultLoginTries
            self.loginTimeout = defaultLoginTimeout
            self.promptPause = defaultPromptPause
            self.commandTimeout = defaultCommandTimeout
            self.loginRegex = defaultLoginRegex
            self.passwordRegex = defaultPasswordRegex
            self.successRegexList = defaultSuccessRegexList
        self.tn = None
        self.cmdprompt = ""
        self.hostname = ""
            
        if log:
            self.log = log
        else:
            logging.basicConfig()
            self.log = logging.getLogger(self.__class__.__name__)
            if options: self.log.setLevel(options.logseverity)
            

    def check(self, hostname, timeout=1):
        "check to see if a device supports telnet"
        from telnetlib import Telnet
        import socket
        try:
            tn = Telnet(hostname)
            index, match, data = tn.expect([self.loginRegex,], timeout)
            tn.close()
            if index == 0: return 1
        except socket.error:
            return 0


    def connect(self, hostname, username, password):
        "login to a machine using telnet"
        self.hostname = hostname
        self.tn = telnetlib.Telnet(hostname)
        loginTries = self.loginTries
        while 1:
            self.tn.expect([self.loginRegex,], self.loginTimeout)
            self.tn.write(username + "\n")
            self.tn.expect([self.passwordRegex,], self.loginTimeout)
            self.tn.write(password + "\n")
            succTest = [self.loginRegex, self.passwordRegex,]
            succTest.extend(self.successRegexList)
            index, match, text = self.tn.expect(succTest, self.loginTimeout) 
            if index < 2: 
                self.log.debug("login failed text returned = '%s'" % text)
                if loginTries <= 1:
                    raise LoginFailed, "login to %s failed" % hostname
                else:
                    loginTries -= 1
            else:
                self.log.info("telnet connection open to device %s" % hostname)
                break
        self.guessCommandPrompt()

    
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
        if not self.cmdprompt: raise NoValidConnection
        if not timeout: timeout = self.commandTimeout
        self.log.debug("executing command '%s'" % command)
        self.tn.write(command + "\n")
        cmdprompt = re.escape(self.cmdprompt)
        index, match, data = self.tn.expect([cmdprompt,], timeout)
        if index < 0: 
            raise CommandTimeout, "command '%s' timeout %.2f" \
                                    % (command, timeout)
        data = data[0:-(len(self.cmdprompt)+1)]
        self.log.debug("data = %s" % data)
        return data


    def disconnect(self):
        "close the telnet session"
        self.tn.write("exit\n")
        self.cmdprompt = ""
        self.log.info("telnet connection to device %s closed" % self.hostname)


    def guessCommandPrompt(self):
        "figure out the command cmdprompt string by issuing a bunch of \ns"
        self.tn.read_very_eager()
        p1 = ""
        p2 = ""
        i = 8 
        while i:
            self.tn.write("\n")
            time.sleep(self.promptPause)
            p1 = self.tn.read_very_eager()
            if p1 == p2: break
            p2 = p1
            p1 = ""
            i -= 1
        if p1:
            self.cmdprompt = p1
            self.log.debug("found cmdprompt = '%s'" % self.cmdprompt)
        else:
            raise NoValidConnection, "no command prompt found"
    

    def findFullCommand(self, command):
        "look through the path list to find the full path to this command"
        if not self.searchPath: return command
        if type(self.searchPath) == type(''):
            self.searchPath = self.searchPath.split(":")
        basecmd = command.split()[0] #remove args
        for path in self.searchPath:
            fullcmd = os.path.join(path, basecmd)
            self._execute(self.existanceCheck % fullcmd)
            if int(self._execute("echo $?")) == 0:
                return os.path.join(path, command)
        self.log.warn('unable to find command %s in search path %s' % 
                                (self.searchPath, command))
            


def main():
    import getpass
    import os
    import sys

    from optparse import OptionParser

    usage = "%prog [options] hostname command"
    parser = OptionParser(usage=usage, 
                               version="%prog " + __version__)
  
    if os.environ.has_key('USER'):
        username = os.environ['USER']
    else:
        username = ''
    parser.add_option('-u', '--user',
                dest='username',
                default=username,
                help='Login username')
    parser.add_option('-p', '--password',
                dest='password',
                default='',
                help='Login password')
    parser.add_option('-t', '--loginTries',
                dest='loginTries',
                type = 'int',
                help='number of times to try login')
    parser.add_option('-l', '--loginTimeout',
                dest='loginTimeout',
                type = 'float',
                help='timeout login expect statments')
    parser.add_option('-P', '--promptPause',
                dest='promptPause',
                type = 'float',
                help='time to pause in prompt discovery loop')
    parser.add_option('-c', '--commandTimeout',
                dest='commandTimeout',
                type = 'float',
                help='timeout when issuing a command')
    parser.add_option('-L', '--loginRegex',
                dest='loginRegex',
                help='regex that will find the login prompt')
    parser.add_option('-w', '--passwordRegex',
                dest='passwordRegex',
                help='regex that will find the password prompt')
    parser.add_option('-s', '--searchPath',
                dest='searchPath',
                default="",
                help='Path to use when looking for commands')
    parser.add_option('-v', '--logseverity',
                dest='logseverity',
                default=logging.INFO,
                type='int',
                help='Logging severity threshold')
        

    options, args = parser.parse_args()
    tt = TelnetSession(searchPath=options.searchPath,options=options)
    if len(args) < 2: 
        parser.print_help()
        sys.exit(1)
    hostname = args[0]
    command = args[1]
    if not options.password:
        password = getpass.getpass()
    else: password = options.password
    tt.connect(hostname, options.username, password)
    import pprint
    pprint.pprint(tt.execute(command, 1.5))
    tt.disconnect()

if __name__ == '__main__':
    main()
