#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""ZenDaemon

Base class for makeing deamon programs

$Id: ZenDaemon.py,v 1.9 2003/08/29 20:33:10 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

import signal
import os
import sys
import socket
import time

from CmdBase import CmdBase

class ZenDaemon(CmdBase):
    
    def __init__(self, noopts=0):
        CmdBase.__init__(self, noopts)
        self.zenhome = os.path.join(os.environ['ZENHOME'])
        self.zenvar = os.path.join(self.zenhome, "var")
        myname = sys.argv[0].split(os.sep)[-1] + ".pid"
        self.pidfile = os.path.join(self.zenvar, myname)
        if not noopts:
            signal.signal(signal.SIGINT, self.sigTerm)
            signal.signal(signal.SIGTERM, self.sigTerm)
            if self.options.daemon and sys.platform != 'win32':
                self.becomeDaemon() 


    def becomeDaemon(self):
        """fork twice to become a daemon"""
        pid = 0
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError, e:
            print >>sys.stderr, ("fork #1 failed: %d (%s)" % 
                    (e.errno, e.strerror))
        os.chdir("/")
        os.setsid()
        os.umask(0)
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError, e:
            print >>sys.stderr, ("fork #2 failed: %d (%s)" % 
                    (e.errno, e.strerror))
        if os.path.exists(self.zenvar):
            file = open(self.pidfile, 'w')
            file.write(str(os.getpid()))
            file.close()
        else:
            print "ERROR: unable to open pid file %s" % pidfile
            sys.exit(1) 


    def sigTerm(self, signum, frame):
        if os.path.exists(self.pidfile):
            self.log.info("delete pidfile %s", self.pidfile)
            os.remove(self.pidfile)
        self.log.info('Daemon %s shutting down' % self.__class__.__name__)
        sys.exit(0)



    def buildOptions(self):
        CmdBase.buildOptions(self)
        self.parser.add_option('-c', '--cycle',
                    dest='cycle',
                    default=0,
                    action="store_true",
                    help="Cycle continuously on cycleInterval from zope")
        self.parser.add_option('-D', '--daemon',
                    dest='daemon',
                    default=0,
                    action="store_true",
                    help="Become a unix daemon")
