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

import rrdtool
import os

class DaemonStats:
    "Utility for a daemon to write out internal performance statistics"

    name = ""
    monitor = ""
    rrdCreateCommand = ""

    def __init__(self):
        pass

    def config(self, name, monitor, rrdCreateCommand = None):
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


    def rrdFile(self, type, cycleTime, names, minVal = 'U', maxVal = 'U'):
        """Create an RRD file if it does not exist."""
        if not self.name: return None
        directory = zenPath('perf', 'Daemons', *names[:-1])
        if not os.path.exists(directory):
            os.makedirs(directory)
        fileName = os.path.join(directory, names[-1] + '.rrd')
        if not os.path.exists(fileName):
            rrdtool.create(fileName,
                           'DS:ds0:%s:%s:%s:%s' % (type,
                                                   cycleTime * 3,
                                                   minVal,
                                                   maxVal),
                           *self.createCommand)
        return fileName
    
    def counter(self, counterName, cycleTime, value):
        "Write a counter value"
        fileName = self.rrdFile('DERIVE',
                                cycleTime,
                                (self.name, self.monitor),
                                0)
        if fileName:
            rrdtool.update(fileName, 'N:%s' % int(value))
        return value

    def gauge(self, counterName, cycleTime, value):
        "Write a gauge value"
        fileName = self.rrdFile('GAUGE',
                                cycleTime,
                                (self.name, self.monitor))
        if fileName:
            rrdtool.update(fileName, 'N:%s' % value)
        return value

