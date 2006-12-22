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
    buffered = d.cacheRRDValue('memBuffer', None)
    cached = d.cacheRRDValue('memCached', None)        
    if totalReal and availableReal:
        percentUsed = Plugin.percent(totalReal -
                                     (availableReal or 0) -
                                     (buffered or 0) -
                                     (cached or 0),
                                     totalReal)
    availableSwap = d.cacheRRDValue('memAvailSwap', None)        
    report.append(Plugin.Record(device=d,
                                totalReal=totalReal,
                                percentUsed=percentUsed,
                                availableReal=availableReal,
                                availableSwap=availableSwap,
                                buffered=buffered,
                                cached=cached))

Plugin.pprint(report, locals())
