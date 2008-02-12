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
import re

class interface:
    "The interface usage report"

    def run(self, dmd, args):
        summary = Utilization.getSummaryArgs(dmd, args)
        report = []
        for d in Utilization.filteredDevices(dmd, args):

            isLocal = re.compile(d.zLocalInterfaceNames)
            for i in d.os.interfaces():
                if isLocal.match(i.name()): continue
                if not i.monitored(): continue
                if i.snmpIgnore(): continue
                if not i.speed: continue
                total = None
                results = i.getRRDValues(['ifHCInOctets',
                                          'ifInOctets',
                                          'ifOutOctets',
                                          'ifHCOutOctets'],
                                         **summary)
                input = results.get('ifHCInOctets',
                                    results.get('ifInOctets', None))
                output = results.get('ifHCOutOctets',
                                     results.get('ifOutOctets', None))

                if None not in [input, output]:
                    total = input + output
                r = Utils.Record(device=d,
                                 interface=i,
                                 speed=i.speed,
                                 input=input,
                                 output=output,
                                 total=total,
                                 percentUsed=Utils.percent(total, i.speed))
                report.append(r)
        return report
