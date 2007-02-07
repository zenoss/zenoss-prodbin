import Globals
from Products.ZenReports import Utils, Utilization

class memory:
    "The memory usage report"

    def run(self, dmd, args):
        summary = Utilization.getSummaryArgs(dmd, args)
        reversedSummary = Utilization.reversedSummary(summary)

        report = []
        freeNames = ['memAvailReal', 'memBuffer', 'memCached']
        fetchNames = ['memoryAvailableKBytes', 'memAvailSwap ', ] + freeNames
        for d in dmd.Devices.getSubDevices():
            totalReal = d.hw.totalMemory
            if not totalReal:
                totalReal = None
            result = d.getRRDValues(fetchNames, **summary) or {}
            winMem = result.get('memoryAvailableKBytes', None)
            availableReal = result.get('memAvailReal', winMem)
            buffered = result.get('memBuffer', None)
            cached = result.get('memCached', None)
            availableSwap = result.get('memAvailSwap', None)
            free = availableReal
            try:
                # max used space space is total - minimum free
                free = d.getRRDSum(freeNames, **reversedSummary)
            except Exception:
                pass

            percentUsed = None
            if totalReal and free:
                percentUsed = Utils.percent(totalReal - free, totalReal)
            r = Utils.Record(device=d,
                             totalReal=totalReal,
                             percentUsed=percentUsed,
                             availableReal=availableReal,
                             availableSwap=availableSwap,
                             buffered=buffered,
                             cached=cached)
            report.append(r)
        return report
