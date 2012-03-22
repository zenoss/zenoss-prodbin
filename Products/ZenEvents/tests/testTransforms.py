###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, 2011, 2012 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenEvents.zeneventd import EventPipelineProcessor
from Products.ZenEvents.events2.processing import DropEvent
from zenoss.protocols.protobufs.zep_pb2 import Event, STATUS_CLOSED, STATUS_SUPPRESSED, SEVERITY_ERROR,\
    SEVERITY_WARNING, SEVERITY_CLEAR
from zenoss.protocols.protobufs.model_pb2 import DEVICE, COMPONENT


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

    def afterSetUp(self):
        super(testTransforms, self).afterSetUp()

        class MockConnection(object):
            def sync(self):
                pass
        self.dmd._p_jar = MockConnection()

        self.processor = EventPipelineProcessor(self.dmd)

    def _processEvent(self, event):
        return self.processor.processMessage(event).event
    
    def testPerfFileSystemTransform(self):
        """
        Test to make sure that the standard transform on the /Perf/Filesystem
        event class works properly for stock performance templates.
        """
        self.dmd.Events.createOrganizer('/Perf/Filesystem')
        self.dmd.Events.Perf.Filesystem.transform = perfFilesystemTransform
        
        # Test an example event from a standard SNMP device.
        device = self.dmd.Devices.createInstance('snmpdevice')
        device.os.addFileSystem('/', False)
        fs = device.os.filesystems()[0]
        fs.mount = '/'
        fs.blockSize = 4096
        fs.totalBlocks = 29221228

        event = Event()
        event.actor.element_identifier = device.id
        event.actor.element_type_id = DEVICE
        event.actor.element_sub_identifier = fs.name()
        event.actor.element_sub_type_id = COMPONENT
        event.severity = SEVERITY_WARNING
        event.event_key = 'usedBlocks_usedBlocks|high disk usage'
        event.event_class = '/Perf/Filesystem'
        event.summary = 'threshold of high disk usage exceeded: current value 23476882.00'

        processed = self._processEvent(event)
        self.assertEquals(processed.summary, 'disk space threshold: 80.3% used (21.9GB free)')
        
        # Test an example event from a standard Perfmon device.
        device = self.dmd.Devices.createInstance('perfmondevice')
        device.os.addFileSystem('C', False)
        fs = device.os.filesystems()[0]
        fs.mount = ' Label:C: Serial Number: 1471843B'
        fs.blockSize = 8192
        fs.totalBlocks = 1047233

        event = Event()
        event.actor.element_identifier = device.id
        event.actor.element_type_id = DEVICE
        event.actor.element_sub_identifier = fs.name()
        event.actor.element_sub_type_id = COMPONENT
        event.severity = SEVERITY_WARNING
        event.event_key = 'FreeMegabytes_FreeMegabytes'
        event.event_class = '/Perf/Filesystem'
        event.summary = 'threshold of low disk space not met: current value 4156.00'
        
        processed = self._processEvent(event)
        self.assertEquals(processed.summary, 'disk space threshold: 49.2% used (4.1GB free)')
    
        # Test an example event from a standard SSH device.
        device = self.dmd.Devices.createInstance('sshdevice')
        device.os.addFileSystem('/', False)
        fs = device.os.filesystems()[0]
        fs.mount = '/'
        fs.blockSize = 1024
        fs.totalBlocks = 149496116

        event = Event()
        event.actor.element_identifier = device.id
        event.actor.element_type_id = DEVICE
        event.actor.element_sub_identifier = fs.id
        event.actor.element_sub_type_id = COMPONENT
        event.severity = SEVERITY_WARNING
        event.event_key = 'disk|disk_usedBlocks|Free Space 90 Percent'
        event.event_class = '/Perf/Filesystem'
        event.summary = 'threshold of Free Space 90 Percent exceeded: current value 73400348.00'

        processed = self._processEvent(event)
        self.assertEquals(processed.summary, 'disk space threshold: 49.1% used (72.6GB free)')

    def testIntSeverityTransform(self):
        """
        Transform the event severity to a string and see if it evaluates.
        """
        transform = 'evt.severity="0"; evt.summary="transformed"'
        self.dmd.Events.createOrganizer('/Perf/Filesystem')
        self.dmd.Events.Perf.Filesystem.transform = transform

        event = Event()
        event.actor.element_identifier = 'localhost'
        event.actor.element_type_id = DEVICE
        event.severity = SEVERITY_ERROR
        event.event_class = '/Perf/Filesystem'
        event.summary = 'bad thingy'

        processed = self._processEvent(event)
        self.assertEqual(SEVERITY_CLEAR, processed.severity)
        self.assertEqual('transformed', processed.summary)
        self.assert_(isinstance(processed.severity, int))

    def testActionDropped(self):
        transform = 'evt._action="drop"'
        self.dmd.Events.createOrganizer('/Perf/Filesystem')
        self.dmd.Events.Perf.Filesystem.transform = transform

        event = Event()
        event.actor.element_identifier = 'localhost'
        event.actor.element_type_id = DEVICE
        event.severity = SEVERITY_ERROR
        event.event_class = '/Perf/Filesystem'
        event.summary = 'should be dropped'

        self.assertRaises(DropEvent, self._processEvent, event)

    def testActionHistory(self):
        transform = 'evt._action="history"'
        self.dmd.Events.createOrganizer('/Perf/Filesystem')
        self.dmd.Events.Perf.Filesystem.transform = transform

        event = Event()
        event.actor.element_identifier = 'localhost'
        event.actor.element_type_id = DEVICE
        event.severity = SEVERITY_ERROR
        event.event_class = '/Perf/Filesystem'
        event.summary = 'should be closed'

        processed = self._processEvent(event)
        self.assertEqual(STATUS_CLOSED, processed.status)

    def testActionStatusDoesntChangeSuppressed(self):
        """
        If an event comes in as suppressed and the _action says to keep it in _status (the default),
        make sure that we don't accidentally change the status of the event back to STATUS_NEW.
        """
        transform = 'evt._action="status"'
        self.dmd.Events.createOrganizer('/Perf/Filesystem')
        self.dmd.Events.Perf.Filesystem.transform = transform

        event = Event()
        event.actor.element_identifier = 'localhost'
        event.actor.element_type_id = DEVICE
        event.severity = SEVERITY_ERROR
        event.status = STATUS_SUPPRESSED
        event.event_class = '/Perf/Filesystem'
        event.summary = 'should be suppressed'

        processed = self._processEvent(event)
        self.assertEqual(STATUS_SUPPRESSED, processed.status)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testTransforms))
    return suite
