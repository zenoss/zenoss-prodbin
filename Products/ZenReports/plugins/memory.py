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

class memory:
    "The memory usage report"

    def run(self, dmd, args):
        summary = Utilization.getSummaryArgs(dmd, args)

        dpNames = [
            'memAvailReal',           # Net-SNMP & SSH
            'memBuffer', 'memCached', # Net-SNMP & SSH on Linux
            'memoryAvailableKBytes',  # SNMP Informant
            'MemoryAvailableBytes',   # Perfmon
            'mem5minFree',            # Cisco
            ]

        report = []
        for d in Utilization.filteredDevices(dmd, args):
            totalReal = d.hw.totalMemory or None
            availableReal = None
            buffered = None
            cached = None
            percentUsed = None

            if d.hw.totalMemory:
                results = d.getRRDValues(dpNames, **summary) or {}

                # UNIX
                if 'memAvailReal' in results:
                    availableReal = results['memAvailReal'] * 1024

                # Linux
                if 'memBuffer' in results and 'memCached' in results \
                    and availableReal is not None:
                    buffered = results['memBuffer'] * 1024
                    cached = results['memCached'] * 1024
                    availableReal += buffered
                    availableReal += cached

                # SNMP Informant
                elif 'memoryAvailableKBytes' in results:
                    availableReal = results['memoryAvailableKBytes'] * 1024

                # Perfmon
                elif 'MemoryAvailableBytes' in results:
                    availableReal = results['MemoryAvailableBytes']

                # Cisco
                elif 'mem5minFree' in results:
                    availableReal = results['mem5minFree']

                if availableReal:
                    percentUsed = Utils.percent(
                        totalReal - availableReal, totalReal)

            r = Utils.Record(device=d,
                             deviceName=d.titleOrId(),
                             totalReal=totalReal,
                             percentUsed=percentUsed,
                             availableReal=availableReal,
                             buffered=buffered,
                             cached=cached)
            report.append(r)
        return report
