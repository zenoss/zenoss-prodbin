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

        if self.options.configfile:
            parseconfig(self.options)

        if os.path.exists(self.options.logconfig):
            logging.config.fileConfig(self.options.logconfig)
        else:
            logging.basicConfig()
        self.log = logging.getLogger(self.__class__.__name__)
        rlog = logging.getLogger()
        rlog.setLevel(self.options.logseverity)


    def setLoggingStream(self, stream):
        from logging import StreamHandler, Formatter
        self.log = logging.getLogger(self.__class__.__name__)
        hdlr = StreamHandler(stream)
        fmt = Formatter(logging.BASIC_FORMAT)
        hdlr.setFormatter(fmt)
        self.log.addHandler(hdlr)
        self.log.setLevel(self.options.logseverity)


    def setWebLoggingStream(self, stream):
        """Setup logging to log to a browser using a request object."""
        from logging import StreamHandler, Formatter
        self.log = logging.getLogger(self.__class__.__name__)
        self.handler = StreamHandler(stream)
        fmt = Formatter("""<tr class="tablevalues">
        <td>%(asctime)s</td><td>%(levelname)s</td>
        <td>%(name)s</td><td>%(message)s</td></tr>
        ""","%Y-%m-%d %H:%M:%S")
        self.handler.setFormatter(fmt)
        self.log.addHandler(self.handler)
        self.log.setLevel(self.options.logseverity)


    def clearWebLoggingStream(self):
        """Clear our web logger."""
        if self.handler and self.log:
            self.log.removeHandler(self.handler)


    def buildOptions(self):
        """basic options setup sub classes can add more options here"""

        self.parser = OptionParser(usage=self.usage, 
                                   version="%prog " + __version__)
        
        self.parser.add_option('-l', '--logconfig',
                    dest='logconfig',
                    default='LoggingConfig.ini',
                    help='Logging configuration file')
        
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
