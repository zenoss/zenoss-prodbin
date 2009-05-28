###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.ZenTestCase.BaseTestCase import BaseTestCase


perfFilesystemTransform = """
if device and evt.eventKey:
    for f in device.os.filesystems():
        if f.name() != evt.component and f.id != evt.component: continue

        # Extract the used blocks from the event's message
        import re
        m = re.search("threshold of [^:]+: current value ([\d\.]+)", evt.message)
        if not m: continue
    
        # Get the total blocks from the model. Adjust by specified offset.
        totalBlocks = f.totalBlocks * getattr(device, "zFileSystemSizeOffset", 1.0)
        totalBytes = totalBlocks * f.blockSize
        usedBytes = None
        
        currentValue = float(m.groups()[0])
        if 'usedBlocks' in evt.eventKey:
            usedBytes = currentValue * f.blockSize
        elif 'FreeMegabytes' in evt.eventKey:
            usedBytes = totalBytes - (currentValue * 1048576)
        else:
            continue
        
        # Calculate the used percent and amount free.
        usedBlocks = float(m.groups()[0])
        p = (usedBytes / totalBytes) * 100
        from Products.ZenUtils.Utils import convToUnits
        free = convToUnits(totalBytes - usedBytes)

        # Make a nicer summary
        evt.summary = "disk space threshold: %3.1f%% used (%s free)" % (p, free)
        evt.message = evt.summary
        break
"""

class testTransforms(BaseTestCase):
    
    def testPerfFileSystemTransform(self):
        """
        Test to make sure that the standard transform on the /Perf/Filesystem
        event class works properly for stock performance templates.
        """
        zem = self.dmd.ZenEventManager
        self.dmd.Events.createOrganizer('/Perf/Filesystem')
        self.dmd.Events.Perf.Filesystem.transform = perfFilesystemTransform
        
        # Test an example event from a standard SNMP device.
        device = self.dmd.Devices.createInstance('snmpdevice')
        device.os.addFileSystem('/', False)
        fs = device.os.filesystems()[0]
        fs.mount = '/'
        fs.blockSize = 4096
        fs.totalBlocks = 29221228
        
        evid = zem.sendEvent(dict(
            device     = device.id,
            severity   = 3,
            component  = fs.name(),
            eventKey   = 'usedBlocks_usedBlocks|high disk usage',
            eventClass = '/Perf/Filesystem',
            summary    = 'threshold of high disk usage exceeded: current value 23476882.00',
            ))
        
        evt = zem.getEventDetailFromStatusOrHistory(evid)
        self.assertEquals(evt.summary, 'disk space threshold: 80.3% used (21.9GB free)')
        
        # Test an example event from a standard Perfmon device.
        device = self.dmd.Devices.createInstance('perfmondevice')
        device.os.addFileSystem('C', False)
        fs = device.os.filesystems()[0]
        fs.mount = ' Label:C: Serial Number: 1471843B'
        fs.blockSize = 8192
        fs.totalBlocks = 1047233
        
        evid = zem.sendEvent(dict(
            device     = device.id,
            severity   = 3,
            component  = fs.name(),
            eventKey   = 'FreeMegabytes_FreeMegabytes',
            eventClass = '/Perf/Filesystem',
            summary    = 'threshold of low disk space not met: current value 4156.00',
            ))
        
        evt = zem.getEventDetailFromStatusOrHistory(evid)
        self.assertEquals(evt.summary, 'disk space threshold: 49.2% used (4.1GB free)')
    
        # Test an example event from a standard SSH device.
        device = self.dmd.Devices.createInstance('sshdevice')
        device.os.addFileSystem('/', False)
        fs = device.os.filesystems()[0]
        fs.mount = '/'
        fs.blockSize = 1024
        fs.totalBlocks = 149496116
        
        evid = zem.sendEvent(dict(
            device     = device.id,
            severity   = 3,
            component  = fs.id,
            eventKey   = 'disk|disk_usedBlocks|Free Space 90 Percent',
            eventClass = '/Perf/Filesystem',
            summary    = 'threshold of Free Space 90 Percent exceeded: current value 73400348.00',
            ))
        
        evt = zem.getEventDetailFromStatusOrHistory(evid)
        self.assertEquals(evt.summary, 'disk space threshold: 49.1% used (72.6GB free)')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testTransforms))
    return suite
