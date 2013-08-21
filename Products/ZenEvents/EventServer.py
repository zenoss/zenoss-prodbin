##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """EventServer

Formerly contained base class 'EventServer' for ZenSyslog, ZenTrap and others.
Stats is still used by ZenSysLog and ZenTrap

$Id$
"""

__version__ = "$Revision$"[11:-2]

import Globals


class Stats:
    totalTime = 0.
    totalEvents = 0
    maxTime = 0.
    
    def add(self, moreTime):
        self.totalEvents += 1
        self.totalTime += moreTime
        self.maxTime = max(self.maxTime, moreTime)

    def report(self):
        return self.totalTime, self.totalEvents, self.maxTime