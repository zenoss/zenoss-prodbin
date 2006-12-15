"The cpu usage report"

import Globals
from Products.ZenReports.plugins import Plugin
dmd, args = Plugin.args(locals())

report = []
for d in dmd.Devices.getSubDevices():
    if not d.monitorDevice(): continue
    laLoadInt5 = d.cacheRRDValue('laLoadInt5', None)
    if laLoadInt5:
        laLoadInt5 /= 100
    idle = d.cacheRRDValue('ssCpuRawIdle', None)
    cpuPercent = None
    if idle is not None:
        cpus = len(d.hw.cpus())
        if cpus:
            cpuPercent = 100 - (idle / cpus)
    if cpuPercent is None:
        cpuPercent = d.cacheRRDValue('cpuPercentProcessorTime', None)
        if cpuPercent:
            cpuPercent /= 100
    r = Plugin.Record(device=d,
                      laLoadInt5=laLoadInt5,
                      cpuPercent=cpuPercent)
    report.append(r)

Plugin.pprint(report, locals())
