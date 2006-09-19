
#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Re-index the event history table.

'''

__version__ = "$Revision$"[11:-2]

import re
import os

try:
    import rrdtool
except ImportError:
    rrdtool = None

import Migrate

rrd = re.compile('.*\\.rrd')

class RRDMinValue(Migrate.Step):
    version = 22.0

    def setMin(self, value):
        for d,_, files in os.walk(os.path.join(os.environ['ZENHOME'], "perf")):
            for f in [f for f in files if rrd.match(f)]:
                rrdtool.tune(os.path.join(d, f), '-i', 'ds0:' + value)

    def cutover(self, dmd):
        if rrdtool:
            self.setMin('U')

RRDMinValue()
