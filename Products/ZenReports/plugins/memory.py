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
                if results.get('memAvailReal', None) is not None:
                    availableReal = results['memAvailReal']

                # Linux
                if results.get('memBuffer', None) is not None \
                    and results.get('memCached', None) is not None \
                    and availableReal is not None:
                    buffered = results['memBuffer']
                    cached = results['memCached']
                    availableReal += buffered
                    availableReal += cached

                # SNMP Informant
                elif results.get('memoryAvailableKBytes', None) is not None:
                    availableReal = results['memoryAvailableKBytes']

                # Perfmon
                elif results.get('MemoryAvailableBytes', None) is not None:
                    availableReal = results['MemoryAvailableBytes']

                # Cisco
                elif results.get('mem5minFree', None) is not None:
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
