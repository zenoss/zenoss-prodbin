#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""ZenDaemon

Base class for makeing deamon programs

$Id: ZenDaemon.py,v 1.9 2003/08/29 20:33:10 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

import sys
import os
import pwd
import signal
import logging

from CmdBase import CmdBase

# Daemon creation code below based on Recipe by Chad J. Schroeder
# File mode creation mask of the daemon.
UMASK = 0
# Default working directory for the daemon.
WORKDIR = "/"

# only close stdin/out/err
MAXFD = 3 

# The standard I/O file descriptors are redirected to /dev/null by default.
if (hasattr(os, "devnull")):
   REDIRECT_TO = os.devnull
else:
   REDIRECT_TO = "/dev/null"


class ZenDaemon(CmdBase):

    pidfile = None
    
    def __init__(self, noopts=0, keeproot=False):
        CmdBase.__init__(self, noopts)
        self.keeproot=keeproot
        self.zenhome = os.path.join(os.environ['ZENHOME'])
        self.zenvar = os.path.join(self.zenhome, "var")
        if not noopts:
            signal.signal(signal.SIGINT, self.sigTerm)
            signal.signal(signal.SIGTERM, self.sigTerm)
            signal.signal(signal.SIGHUP, self.sigTerm)
            if self.options.daemon:
                self.changeUser()
                self.becomeDaemon() 


    def setupLogging(self):
        rlog = logging.getLogger()
        rlog.setLevel(logging.WARN)
        mname = self.__class__.__name__
        self.log = logging.getLogger("zen."+ mname)
        zlog = logging.getLogger("zen")
        zlog.setLevel(self.options.logseverity)
        if self.options.daemon or self.options.logpath:
            if self.options.logpath:
                if not os.path.isdir(os.path.dirname(self.options.logpath)):
                    raise SystemExit("logpath:%s doesn't exist" %
                                        self.options.logpath)
                logdir = self.options.logpath
            else:
                logdir = os.path.join(os.environ['ZENHOME'], "log")
            logfile = os.path.join(logdir, mname.lower()+".log")
            h = logging.FileHandler(logfile)
            h.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s",
                "%Y-%m-%d %H:%M:%S"))
            rlog.addHandler(h)
        else:
            logging.basicConfig()


    def changeUser(self):
        if not self.keeproot:
            try:
                cname = pwd.getpwuid(os.getuid())[0]
                pwrec = pwd.getpwnam(self.options.uid)
                os.setuid(pwrec.pw_uid)
                os.environ['HOME'] = pwrec.pw_dir
            except KeyError:
                print >>sys.stderr, "WARN: user:%s not found running as:%s"%(
                                    self.options.uid,cname)


    def becomeDaemon(self):
        """Code below comes from the excelent recipe by Chad J. Schroeder.
        """
        try:
            pid = os.fork()
        except OSError, e:
            raise Exception, "%s [%d]" % (e.strerror, e.errno)

        if (pid == 0):	# The first child.
            os.setsid()
            try:
                pid = os.fork()	# Fork a second child.
            except OSError, e:
                raise Exception, "%s [%d]" % (e.strerror, e.errno)

            if (pid == 0):	# The second child.
                os.chdir(WORKDIR)
                os.umask(UMASK)
            else:
                os._exit(0)	# Exit parent (the first child) of the second child.
        else:
            os._exit(0)	# Exit parent of the first child.

        # Iterate through and close all stdin/out/err
        for fd in range(0, MAXFD):
            try:
                os.close(fd)
            except OSError:	# ERROR, fd wasn't open to begin with (ignored)
                pass

        os.open(REDIRECT_TO, os.O_RDWR)	# standard input (0)
        # Duplicate standard input to standard output and standard error.
        os.dup2(0, 1)			# standard output (1)
        os.dup2(0, 2)			# standard error (2)
        if os.path.exists(self.zenvar):
            myname = sys.argv[0].split(os.sep)[-1] + ".pid"
            self.pidfile = os.path.join(self.zenvar, myname)
            fp = open(self.pidfile, 'w')
            fp.write(str(os.getpid()))
            fp.close()
        else:
            raise SystemExit("ERROR: unable to open pid file %s" % self.pidfile)
        return(0)


    def sigTerm(self, *unused):
        stop = getattr(self, "stop", None)
        if callable(stop): stop()
        if self.pidfile and os.path.exists(self.pidfile):
            self.log.info("delete pidfile %s", self.pidfile)
            os.remove(self.pidfile)
        self.log.info('Daemon %s shutting down' % self.__class__.__name__)
        raise SystemExit


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
