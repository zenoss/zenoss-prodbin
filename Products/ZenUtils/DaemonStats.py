##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Globals
from Products.ZenUtils.Utils import zenPath

# FIXME dependency from Utils to Thresholds
from Products.ZenRRD.Thresholds import Thresholds

import rrdtool
import os
import time

import logging
log = logging.getLogger("zen.DaemonStats")

def fullname(partial):
    return zenPath('perf', partial + '.rrd')

class DaemonStats(object):
    "Utility for a daemon to write out internal performance statistics"

    def __init__(self):
        self.name = ""
        self.monitor = ""
        self.rrdCreateCommand = ""

        self.thresholds = Thresholds()


    def config(self, name, monitor, thresholds, rrdCreateCommand = None):
        """Initialize the object.  We could do this in __init__, but
        that would delay creation to after configuration time, which
        may run asynchronously with collection or heartbeats.  By
        deferring initialization, this object implements the Null
        Object pattern until the application is ready to start writing
        real statistics.
        """
        self.name = name
        self.monitor = monitor
        if not rrdCreateCommand:
            from Products.ZenModel.PerformanceConf import PerformanceConf
            rrdCreateCommand = PerformanceConf.defaultRRDCreateCommand
        if not isinstance(rrdCreateCommand, basestring):
            self.createCommand = rrdCreateCommand
        else:
            self.createCommand = rrdCreateCommand.split('\n')
        self.thresholds = Thresholds()
        self.thresholds.updateList(thresholds)


    def rrdFile(self, type, cycleTime, name, minVal = 'U', maxVal = 'U'):
        """Create an RRD file if it does not exist.
        Returns the basename of the rrdFile, suitable for checking thresholds.
        """
        if not self.name: return None
        base = os.path.join('Daemons', self.name)
        directory = zenPath('perf', base)
        if not os.path.exists(directory):
            os.makedirs(directory)
        base = os.path.join(base, '%s_%s' % (self.monitor, name))
        fileName = fullname(base)
        if not os.path.exists(fileName):
            rrdtool.create(fileName,
                           '--step', "%d" % cycleTime,
                           'DS:ds0:%s:%s:%s:%s' % (type,
                                                   cycleTime * 3,
                                                   minVal,
                                                   maxVal),
                           *self.createCommand)
        return base


    def derive(self, name, cycleTime, value):
        "Write a DERIVE value, return threshold events"
        return self.counter(name, cycleTime, value)

    def counter(self, name, cycleTime, value):
        "Write a DERIVE(! NOT COUNTER!) value, return threshold events"
        fileName = self.rrdFile('DERIVE', cycleTime, name, 0)
        if fileName:
            full = fullname(fileName)
            try:
                rrdtool.update(full, 'N:%s' % int(value))
                startStop, names, values = \
                    rrdtool.fetch(full, 'AVERAGE',
                        '-s', 'now-%d' % (cycleTime*2),
                        '-e', 'now')
                value = values[0][0]
                if value is not None:
                    return self.thresholds.check(fileName, time.time(), value)
            except rrdtool.error, err:
                log.error('rrdtool reported error %s %s', err, full)
        return []


    def gauge(self, name, cycleTime, value):
        "Write a gauge value, return threshold events"
        fileName = self.rrdFile('GAUGE', cycleTime, name)
        if fileName:
            full = fullname(fileName)
            try:
                rrdtool.update(full, 'N:%s' % value)
            except rrdtool.error, err:
                log.error('rrdtool reported error %s %s', err, full)
        if value is not None:
            return self.thresholds.check(fileName, time.time(), value)
        return []
