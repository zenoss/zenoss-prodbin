#################################################################
#
#   Copyright (c) 2003 Zentinel Systems, Inc. All rights reserved.
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
        self.buildOptions()
        self.parseOptions()
        self.setupLogging()
        if self.options.configfile:
            parseconfig(self.options)


    def setupLogging(self):
        """Setup logging to send to stdout. zen.* logged at --logseverity
        root at ERROR.
        """
        logging.basicConfig()
        rlog = logging.getLogger()
        rlog.setLevel(logging.ERROR)
        zlog = logging.getLogger("zen")
        zlog.setLevel(self.options.logseverity)
        self.log = logging.getLogger("zen."+self.__class__.__name__)


    def setLoggingStream(self, stream):
        from logging import StreamHandler, Formatter
        hdlr = StreamHandler(stream)
        fmt = Formatter(logging.BASIC_FORMAT)
        hdlr.setFormatter(fmt)
        rlog = logging.getLogger()
        rlog.addHandler(hdlr)
        rlog.setLevel(logging.ERROR)
        zlog = logging.getLogger("zen")
        zlog.setLevel(self.options.logseverity)
        self.log = logging.getLogger("zen."+self.__class__.__name__)
        

    def buildOptions(self):
        """basic options setup sub classes can add more options here"""

        self.parser = OptionParser(usage=self.usage, 
                                   version="%prog " + __version__)
        
        self.parser.add_option('-v', '--logseverity',
                    dest='logseverity',
                    default=20,
                    type='int',
                    help='Logging severity threshold')
        
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
