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

class DaemonStats:
    "Utility for a daemon to write out internal performance statistics"

    name = ""
    monitor = ""
    rrdCreateCommand = ""

    def __init__(self):
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
        if type(rrdCreateCommand) != type(''):
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
                           'DS:ds0:%s:%s:%s:%s' % (type,
                                                   cycleTime * 3,
                                                   minVal,
                                                   maxVal),
                           *self.createCommand)
        return base


    def counter(self, name, cycleTime, value):
        "Write a counter value, return threshold events"
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
