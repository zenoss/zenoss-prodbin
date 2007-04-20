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

class filesystems:
    "The file systems report"

    def run(self, dmd, args):
        report = []
        summary = Utilization.getSummaryArgs(dmd, args)
        for d in dmd.Devices.getSubDevices():
            for f in d.os.filesystems():
                if not f.monitored(): continue
                available, used = None, None
                used = f.getRRDValue('usedBlocks', **summary)
                if used:
                    used = long(used * f.blockSize)
                    available = f.totalBytes() - used
                percent = Utils.percent(used, f.totalBytes())
                r = Utils.Record(device=d,
                                 deviceName=d.id,
                                 filesystem=f,
                                 mount=f.mount,
                                 usedBytes=used,
                                 availableBytes=available,
                                 percentFull=percent,
                                 totalBytes=f.totalBytes())
                report.append(r)
        return report
