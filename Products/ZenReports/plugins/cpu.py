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
from Products.ZenReports import Utils, Utilization

class cpu:
    "The cpu usage report"
    
    def run(self, dmd, args):
        summary = Utilization.getSummaryArgs(dmd, args)

        # maximum use is minimum idle
        idleSummary = Utilization.reversedSummary(summary)

        report = []
        for d in Utilization.filteredDevices(dmd, args):

            laLoadInt5 = d.getRRDValue('laLoadInt5', **summary)
            if laLoadInt5 is not None:
                laLoadInt5 = laLoadInt5 / 100.0
            cpuPercent = None

            idle = d.getRRDValue('ssCpuRawIdle', **idleSummary)
            if idle is not None:
                cpus = len(d.hw.cpus())
                if cpus:
                    cpuPercent = max(100 - (idle / cpus), 0)

            if cpuPercent is None:
                cpuPercent = d.getRRDValue('cpuPercentProcessorTime', **summary)
                if cpuPercent is not None:
                    cpuPercent /= 100

            if cpuPercent is None:
                cpuPercent = d.getRRDValue('cpu5min', **summary)
                if cpuPercent is not None:
                    cpuPercent /= 100

            r = Utils.Record(device=d,
                             laLoadInt5=laLoadInt5,
                             cpuPercent=cpuPercent)
            report.append(r)
        return report
