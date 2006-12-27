"The file systems report"

import Globals
from Products.ZenReports.plugins import Plugin, Utilization
dmd, args = Plugin.args(locals())

summary = Utilization.getSummaryArgs(dmd, args)

report = []
for d in dmd.Devices.getSubDevices():
    for f in d.os.filesystems():
        if f.monitored():
            available, used = None, None
            used = f.getRRDValue('usedBlocks', **summary)
            if used:
                used = long(used * f.blockSize)
                available = f.totalBytes() - used
            percent = Plugin.percent(used, f.totalBytes())
            report.append(Plugin.Record(device=d,
                                        deviceName=d.id,
                                        filesystem=f,
                                        mount=f.mount,
                                        usedBytes=used,
                                        availableBytes=available,
                                        percentFull=percent))

Plugin.pprint(report, globals())
