##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Allow the RRD data source to go negative. 

'''

__version__ = "$Revision$"[11:-2]

import os
import re

import rrdtool

import Migrate

rrd = re.compile('.*\\.rrd')

from Products.ZenUtils.Utils import zenPath
class RRDMinValue(Migrate.Step):
    version = Migrate.Version(0, 22, 0)

    def setMin(self, value):
        for d,_, files in os.walk(zenPath("perf")):
            for f in [f for f in files if rrd.match(f)]:
                rrdtool.tune(os.path.join(d, f), '-i', 'ds0:' + value)

    def cutover(self, unused):
        if rrdtool:
            self.setMin('U')

RRDMinValue()
