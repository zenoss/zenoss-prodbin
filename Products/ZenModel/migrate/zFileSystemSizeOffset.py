###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__='''

Add zFileSystemSizeOffset to DeviceClass.

'''
import Migrate

perfFilesystemTransform = """if device:
    for f in device.os.filesystems():
        if f.name() != evt.component: continue

        # Extract the used blocks from the event's message
        import re
        m = re.search("threshold of [^:]+: current value ([\d\.]+)", evt.message)
        if not m: continue

        # Get the total blocks from the model. Adjust by specified offset.
        totalBlocks = f.totalBlocks * getattr(device, "zFileSystemSizeOffset", 1.0)
    
        # Calculate the used percent and amount free.
        usedBlocks = float(m.groups()[0])
        p = (usedBlocks / totalBlocks) * 100
        freeAmtGB = ((totalBlocks - usedBlocks) * f.blockSize) / 1073741824

        # Make a nicer summary
        evt.summary = "disk space threshold: %3.1f%% used (%3.2f GB free)" % (p, freeAmtGB)
        evt.message = evt.summary
        break"""

class zFileSystemSizeOffset(Migrate.Step):
    version = Migrate.Version(2, 4, 0)
    
    def cutover(self, dmd):
        # Install the zFileSystemSizeOffset zProperty
        if not dmd.Devices.hasProperty('zFileSystemSizeOffset'):
            dmd.Devices._setProperty('zFileSystemSizeOffset', 1.0, type="float")
        
        # Install the /Perf/Filesystem transform
        try:
            ec = dmd.Events.Perf.Filesystem
            if not ec.transform:
                ec.transform = perfFilesystemTransform
        except AttributeError:
            pass
        
        # Fix thresholds and graph RPNs
        for t in dmd.Devices.getAllRRDTemplates():
            if t.id != "FileSystem": continue
            
            try:
                if t.datasources()[0].oid != "1.3.6.1.2.1.25.2.3.1.6":
                    continue
            except Exception:
                continue
            
            for th in t.thresholds():
                if "zFileSystemSizeOffset" not in th.maxval:
                    th.maxval = th.maxval.replace("here.totalBlocks",
                        "(here.totalBlocks * here.zFileSystemSizeOffset)")
                if "zFileSystemSizeOffset" not in th.minval:
                    th.minval = th.minval.replace("here.totalBlocks",
                        "(here.totalBlocks * here.zFileSystemSizeOffset)")
            
            for g in t.graphDefs():
                for gp in g.graphPoints():
                    if not hasattr(gp, "rpn"): continue
                    if "zFileSystemSizeOffset" in gp.rpn: continue
                    gp.rpn = gp.rpn.replace("${here/totalBlocks}",
                        "${here/totalBlocks},${here/zFileSystemSizeOffset},*")


zFileSystemSizeOffset()

