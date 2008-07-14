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

__doc__="""ZenDaemon

Base class for making deamon programs

$Id: ZenDaemon.py,v 1.9 2003/08/29 20:33:10 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

import sys
import os
import pwd
import logging

from CmdBase import CmdBase
from Utils import zenPath, HtmlFormatter, binPath

# Daemon creation code below based on Recipe by Chad J. Schroeder
# File mode creation mask of the daemon.
UMASK = 0022
# Default working directory for the daemon.
WORKDIR = "/"

# only close stdin/out/err
MAXFD = 3 

# The standard I/O file descriptors are redirected to /dev/null by default.
if (hasattr(os, "devnull")):
   REDIRECT_TO = os.devnull
else:
   REDIRECT_TO = "/dev/null"

DEFAULT_START_TIMEOUT = 10*60*60

class ZenDaemon(CmdBase):

    pidfile = None
    
    def __init__(self, noopts=0, keeproot=False):
        CmdBase.__init__(self, noopts)
        self.pidfile = 'unknown'
        self.keeproot=keeproot
        self.reporter = None
        from twisted.internet import reactor
        reactor.addSystemEventTrigger('before', 'shutdown', self.sigTerm)
        if not noopts:
            if self.options.daemon:
                self.changeUser()
                self.becomeDaemon()
        # if we are daemonizing non-watchdog, or child of a watchdog:
        if ((self.options.daemon and not self.options.watchdog) or 
            self.options.watchdogPath):
           try:
              self.writePidFile()
           except OSError:
              raise SystemExit("ERROR: unable to open pid file %s" %
                               self.pidfile)
        if self.options.watchdog and not self.options.watchdogPath:
            self.becomeWatchdog()


    def openPrivilegedPort(self, *address):
        """Execute under zensocket, providing the args to zensocket"""
        zensocket = binPath('zensocket')
        cmd = [zensocket, zensocket] + list(address) + ['--'] + \
              [sys.executable] + sys.argv + \
              ['--useFileDescriptor=$privilegedSocket']
        os.execlp(*cmd)


    def writePidFile(self):
        myname = sys.argv[0].split(os.sep)[-1]
        if myname.endswith('.py'): myname = myname[:-3]
        monitor = getattr(self.options, 'monitor', 'localhost')
        myname = "%s-%s.pid" % (myname, monitor)
        if self.options.watchdog:
           self.pidfile =  zenPath("var", 'watchdog-%s' % myname)
        else:
           self.pidfile =  zenPath("var", myname)
        fp = open(self.pidfile, 'w')
        fp.write(str(os.getpid()))
        fp.close()

    def setupLogging(self):
        rlog = logging.getLogger()
        rlog.setLevel(logging.WARN)
        mname = self.__class__.__name__
        self.log = logging.getLogger("zen."+ mname)
        zlog = logging.getLogger("zen")
        zlog.setLevel(self.options.logseverity)
        if self.options.watchdogPath or \
           self.options.daemon:
            if self.options.logpath:
                if not os.path.isdir(os.path.dirname(self.options.logpath)):
                    raise SystemExit("logpath:%s doesn't exist" %
                                        self.options.logpath)
                logdir = self.options.logpath
            else:
                logdir = zenPath("log")
            logfile = os.path.join(logdir, mname.lower()+".log")
            h = logging.FileHandler(logfile)
            h.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s",
                "%Y-%m-%d %H:%M:%S"))
            rlog.addHandler(h)
        else:
            logging.basicConfig()
            if self.options.weblog:
                [ h.setFormatter(HtmlFormatter()) for h in rlog.handlers ]


    def changeUser(self):
        if not self.keeproot:
            try:
                cname = pwd.getpwuid(os.getuid())[0]
                pwrec = pwd.getpwnam(self.options.uid)
                os.setuid(pwrec.pw_uid)
                os.environ['HOME'] = pwrec.pw_dir
            except (KeyError, OSError):
                print >>sys.stderr, "WARN: user:%s not found running as:%s"%(
                                    self.options.uid,cname)


    def becomeDaemon(self):
        """Code below comes from the excellent recipe by Chad J. Schroeder.
        """
        try:
            pid = os.fork()
        except OSError, e:
            raise Exception, "%s [%d]" % (e.strerror, e.errno)

        if (pid == 0):  # The first child.
            os.setsid()
            try:
                pid = os.fork() # Fork a second child.
            except OSError, e:
                raise Exception, "%s [%d]" % (e.strerror, e.errno)

            if (pid == 0):      # The second child.
                os.chdir(WORKDIR)
                os.umask(UMASK)
            else:
                os._exit(0)     # Exit parent (the first child) of the second child.
        else:
            os._exit(0) # Exit parent of the first child.

        # Iterate through and close all stdin/out/err
        for fd in range(0, MAXFD):
            try:
                os.close(fd)
            except OSError:     # ERROR, fd wasn't open to begin with (ignored)
                pass

        os.open(REDIRECT_TO, os.O_RDWR) # standard input (0)
        # Duplicate standard input to standard output and standard error.
        os.dup2(0, 1)                   # standard output (1)
        os.dup2(0, 2)                   # standard error (2)


    def sigTerm(self, signum=None, frame=None):
        # This probably won't be called when running as daemon.
        # See ticket #1757
        from Products.ZenUtils.Utils import unused
        unused(signum, frame)
        stop = getattr(self, "stop", None)
        if callable(stop): stop()
        if self.pidfile and os.path.exists(self.pidfile):
            self.log.info("delete pidfile %s", self.pidfile)
            os.remove(self.pidfile)
        self.log.info('Daemon %s shutting down' % self.__class__.__name__)
        raise SystemExit

    def becomeWatchdog(self):
        from Products.ZenUtils.Watchdog import Watcher, log
        log.setLevel(self.options.logseverity)
        cmd = sys.argv[:]
        if '--watchdog' in cmd:
            cmd.remove('--watchdog')
        if '--daemon' in cmd:
            cmd.remove('--daemon')
        socketPath = '%s/.%s-watchdog-%d' % (
            zenPath('var'), self.__class__.__name__, os.getpid())
        # time between child reports: default to 2x the default cycle time
        cycleTime = getattr(self.options, 'cycleTime', 1200)
        startTimeout = getattr(self.options, 'starttimeout', DEFAULT_START_TIMEOUT)
        maxTime = getattr(self.options, 'maxRestartTime', 600)
        watchdog = Watcher(socketPath,
                           cmd,
                           startTimeout,
                           cycleTime,
                           maxTime)
        watchdog.run()
        sys.exit(0)

    def niceDoggie(self, timeout):
        # defer creation of the reporter until we know we're not going
        # through zensocket or other startup that results in closing
        # this socket
        if not self.reporter and self.options.watchdogPath:
            from Watchdog import Reporter
            self.reporter = Reporter(self.options.watchdogPath)
        if self.reporter:
           self.reporter.niceDoggie(timeout)

    def buildOptions(self):
        CmdBase.buildOptions(self)
        self.parser.add_option('--uid',dest='uid',default="zenoss",
                help='user to become when running default:zenoss')
        self.parser.add_option('-c', '--cycle',dest='cycle',
                action="store_true", default=False,
                help="Cycle continuously on cycleInterval from zope")
        self.parser.add_option('-D', '--daemon', default=False,
                dest='daemon',action="store_true",
                help="Become a unix daemon")
        self.parser.add_option('--weblog', default=False,
                dest='weblog',action="store_true",
                help="output log info in html table format")
        self.parser.add_option('--watchdog', default=False,
                               dest='watchdog', action="store_true",
                               help="Run under a supervisor which will restart it")
        self.parser.add_option('--watchdogPath', default=None,
                               dest='watchdogPath', 
                               help="The path to the watchdog reporting socket")
        self.parser.add_option('--startTimeOut',
                               dest='starttimeout',
                               type="int",
                               default=DEFAULT_START_TIMEOUT,
                               help="wait seconds for initial heartbeat")


