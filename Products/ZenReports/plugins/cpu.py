"The cpu usage report"

import Globals
from Products.ZenReports.plugins import Plugin, Utilization
from Products.ZenUtils import Time

dmd, args = Plugin.args(locals())
summary = Utilization.getSummaryArgs(dmd, args)

# maximum use is minimum idle
idleSummary = Utilization.reversedSummary(summary)

report = []
for d in dmd.Devices.getSubDevices():
    if not d.monitorDevice(): continue

    laLoadInt5 = d.getRRDValue('laLoadInt5', **summary)
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

    r = Plugin.Record(device=d,
                      laLoadInt5=laLoadInt5,
                      cpuPercent=cpuPercent)
    report.append(r)

Plugin.pprint(report, locals())
