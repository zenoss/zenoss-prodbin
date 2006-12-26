"The memory usage report"

import Globals
from Products.ZenReports.plugins import Plugin, Utilization
dmd, args = Plugin.args(locals())

summary = Utilization.getSummaryArgs(dmd, args)

report = []
fetchNames = [
    'memoryAvailableKBytes',
    'memAvailSwap ', 'memAvailReal', 'memBuffer', 'memCached'
    ]
for d in dmd.Devices.getSubDevices():
    totalReal = d.hw.totalMemory
    if not totalReal:
        totalReal = None
    result = d.getRRDValues(fetchNames, **summary) or {}
    winMem = result.get('memoryAvailableKBytes', None)
    availableReal = result.get('memAvailReal', winMem)
    percentUsed = None
    buffered = result.get('memBuffer', None)
    cached = result.get('memCached', None)
    availableSwap = result.get('memAvailSwap', None)
    
    if totalReal and availableReal:
        percentUsed = Plugin.percent(totalReal -
                                     (availableReal or 0) -
                                     (buffered or 0) -
                                     (cached or 0),
                                     totalReal)
    report.append(Plugin.Record(device=d,
                                totalReal=totalReal,
                                percentUsed=percentUsed,
                                availableReal=availableReal,
                                availableSwap=availableSwap,
                                buffered=buffered,
                                cached=cached))

Plugin.pprint(report, locals())
