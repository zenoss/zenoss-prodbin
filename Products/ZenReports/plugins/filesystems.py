"The file systems report"

import Plugin
dmd, args = Plugin.args(globals())

report = []
for d in dmd.Devices.getSubDevices():
    for f in d.os.filesystems():
        percent = None
        try:
            percent = f.usedBlocks() * 100. / f.totalBlocks
        except TypeError:
            pass
        report.append(Plugin.Record(device=d.id,
                                    filesystem=f.title,
                                    percent=percent))

Plugin.pprint(report, globals())
