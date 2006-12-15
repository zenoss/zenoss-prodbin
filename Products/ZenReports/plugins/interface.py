"The interface usage report"

import Globals
from Products.ZenReports.plugins import Plugin
dmd, args = Plugin.args(locals())

report = []
for d in dmd.Devices.getSubDevices():
    for i in d.os.interfaces():
        if not i.monitored(): continue
        total = None
        input = i.cacheRRDValue('ifInOctets', None)
        output = i.cacheRRDValue('ifOutOctets', None)
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
