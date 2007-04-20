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


__doc__='''

Allow the RRD data source to go negative. 

'''

__version__ = "$Revision$"[11:-2]

import os
import re

try:
    import rrdtool
except ImportError:
    rrdtool = None

import Migrate

rrd = re.compile('.*\\.rrd')

class RRDMinValue(Migrate.Step):
    version = Migrate.Version(0, 22, 0)

    def setMin(self, value):
        for d,_, files in os.walk(os.path.join(os.environ['ZENHOME'], "perf")):
            for f in [f for f in files if rrd.match(f)]:
                rrdtool.tune(os.path.join(d, f), '-i', 'ds0:' + value)

    def cutover(self, dmd):
        if rrdtool:
            self.setMin('U')

RRDMinValue()
