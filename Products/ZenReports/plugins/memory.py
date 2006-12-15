"The memory usage report"

import Globals
from Products.ZenReports.plugins import Plugin
dmd, args = Plugin.args(locals())

report = []
for d in dmd.Devices.getSubDevices():
    totalReal=d.hw.totalMemory
    if not totalReal:
        totalReal = None
    winMem = d.cacheRRDValue('memoryAvailableKBytes', None)
    availableReal=d.cacheRRDValue('memAvailReal', winMem)
    percentUsed = None
    if totalReal and availableReal:
        percentUsed = Plugin.percent(totalReal - availableReal, totalReal)
    report.append(Plugin.Record(device=d,
                                totalReal=totalReal,
                                percentUsed=percentUsed,
                                availableReal=availableReal,
                                availableSwap=d.cacheRRDValue('memAvailSwap',
                                                              None),
                                buffered=d.cacheRRDValue('memBuffer', None),
                                cached=d.cacheRRDValue('memCached', None)))

Plugin.pprint(report, locals())
