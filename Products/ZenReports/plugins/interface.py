"The interface usage report"

import Globals
from Products.ZenReports.plugins import Plugin, Utilization

dmd, args = Plugin.args(locals())
summary = Utilization.getSummaryArgs(dmd, args)

report = []
for d in dmd.Devices.getSubDevices():
    for i in d.os.interfaces():
        if not i.monitored(): continue
        if i.snmpIgnore(): continue
        total = None
        input = i.getRRDValue('ifInOctets', **summary)
        output = i.getRRDValue('ifOutOctets', **summary)

        if None not in [input, output]:
            total = input + output
        r = Plugin.Record(device=d,
                          interface=i,
                          speed=i.speed,
                          input=input,
                          output=output,
                          total=total,
                          percentUsed=Plugin.percent(total, i.speed))
        report.append(r)

Plugin.pprint(report, locals())
