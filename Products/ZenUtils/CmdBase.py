#################################################################
#
#   Copyright (c) 2003 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""CmdBase

Provide utility functions for logging and config file parsing
to command line programs


$Id: CmdBase.py,v 1.10 2004/04/04 02:22:21 edahl Exp $"""

__version__ = "$Revision: 1.10 $"[11:-2]

import os
import logging
import logging.config
from optparse import OptionParser

from Utils import parseconfig

class DMDError: pass

class CmdBase:

    def __init__(self, noopts=0):
        self.usage = "%prog [options]"
        self.noopts = noopts
        self.args = []
        self.parser = None
        self.buildParser()
        self.buildOptions()
        self.parseOptions()
        if self.options.configfile:
            parseconfig(self.options)
        self.setupLogging()


    def setupLogging(self):
        rlog = logging.getLogger()
        rlog.setLevel(logging.WARN)
        mname = self.__class__.__name__
        self.log = logging.getLogger("zen."+ mname)
        zlog = logging.getLogger("zen")
        zlog.setLevel(self.options.logseverity)
        if self.options.logpath:
            logdir = self.options.logpath
            if not os.path.isdir(os.path.dirname(logdir)):
                raise SystemExit("logpath:%s doesn't exist" % logdir)
            logfile = os.path.join(logdir, mname.lower()+".log")
            h = logging.FileHandler(logfile)
            h.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s",
                "%Y-%m-%d %H:%M:%S"))
            rlog.addHandler(h)
        else:
            logging.basicConfig()


    def buildParser(self):
        if not self.parser:
            self.parser = OptionParser(usage=self.usage, 
                                       version="%prog " + __version__)

    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        self.buildParser()
        self.parser.add_option('-v', '--logseverity',
                    dest='logseverity',
                    default=20,
                    type='int',
                    help='Logging severity threshold')
        self.parser.add_option('--logpath',dest='logpath',
                    help='override default logging path')
        self.parser.add_option("-C", "--configfile", 
                    dest="configfile",
                    help="config file must define all params (see man)")



    def parseOptions(self):
        if self.noopts:
            args = []
        else:
            import sys
            args = sys.argv[1:]
        (self.options, self.args) = self.parser.parse_args(args=args)
