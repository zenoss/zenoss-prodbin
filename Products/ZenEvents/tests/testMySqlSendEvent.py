###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.ZenTestCase.BaseTestCase import BaseTestCase

TEST_DEVICE = 'TestDeviceSE'
IPADDR1 = '1.1.1.1'
IPADDR2 = '1.1.1.2'


class MySqlSendEventTest(BaseTestCase):
    
    def setUp(self):
        BaseTestCase.setUp(self)
        self.zem = self.dmd.ZenEventManager
        self.d = self.dmd.Devices.createInstance(TEST_DEVICE)

    def tearDown(self):
        conn = self.zem.connect()
        try:
            curs = conn.cursor()
            curs.execute("truncate table status")
            curs.execute("truncate table history")
            curs.execute("truncate table detail")
            curs.execute("truncate table heartbeat")
        finally: 
            self.zem.close(conn)
        BaseTestCase.tearDown(self)


    def testSendEventDeviceFieldIsName(self):
        """Send event with device feild set to name of device"""
        evt = dict(device = TEST_DEVICE, 
                    summary = 'device field is name using device index', 
                    severity = 5)
        evid = self.zem.sendEvent(evt)
        event = self.zem.getEventDetail(evid)
        self.assert_(event.device == TEST_DEVICE)

    def testSendEventDeviceFieldIsIp(self): 
        """Send event with device feild set to manage ip of device"""
        self.d.setManageIp(IPADDR1)
        evt = dict(device = IPADDR1, 
                    summary = 'device field is ip using device index', 
                    severity = 5)
        evid = self.zem.sendEvent(evt)
        event = self.zem.getEventDetail(evid)
        self.assert_(event.device == TEST_DEVICE)

    def testSendEventDeviceFieldIsIpNet(self):
        """Send event with device feild set to an interface ip of device"""
        self.d.os.addIpInterface('eth0', True)
        self.d.os.interfaces.eth0.addIpAddress(IPADDR2)
        evt = dict(device = IPADDR2, 
                summary = 'device field is ip using network index', 
                severity = 5)
        evid = self.zem.sendEvent(evt)
        event = self.zem.getEventDetail(evid)
        self.assert_(event.device == TEST_DEVICE)


    def testSendEvent_ipAddressFieldIsIpNet(self):
        """Send event with ipAddress feild set to an interface ip of device"""
        self.d.os.addIpInterface('eth0', True)
        self.d.os.interfaces.eth0.addIpAddress(IPADDR2)
        evt = dict(device = "", ipAddress = IPADDR2, 
                summary = 'device blank, ipAddress with ip using network index',
                severity = 5)
        evid = self.zem.sendEvent(evt)
        event = self.zem.getEventDetail(evid)
        self.assert_(event.device == TEST_DEVICE)
        self.assert_(event.ipAddress == IPADDR2)


    def testDeduplicationSimple(self):
        """Test sumary based dedupliation 
        """
        evt = dict(device=TEST_DEVICE, summary='Test', severity = 5)
        evid = self.zem.sendEvent(evt)
        evid2 = self.zem.sendEvent(evt)
        self.assert_(evid == evid2)


    def testDeduplicationEventKey(self):
        """
        Test eventKey based dedupliation events have different summaries but
        same eventKey
        """
        evt = dict(device=TEST_DEVICE, eventKey='mykey',
                    summary='Test', severity = 5)
        evid = self.zem.sendEvent(evt)
        evt = dict(device=TEST_DEVICE, eventKey='mykey',
                    summary='Test2', severity = 5)
        evid2 = self.zem.sendEvent(evt)
        self.assert_(evid == evid2)


    def testUnknownEventClass(self):
        """Test event with no eventClass getting class set to /Unknown
        """
        evt = dict(device=TEST_DEVICE, summary='Test', severity = 5)
        evid = self.zem.sendEvent(evt)
        event = self.zem.getEventDetail(evid)
        self.assert_(event.eventClass == "/Unknown")


    def testHeartbeatClass(self):
        """Test sending heartbeats and the not timedout query
        """
        evt = dict(device=TEST_DEVICE, summary='Test', component='Test', 
                    timeout = 50, severity = 5, eventClass="/Heartbeat")
        evid = self.zem.sendEvent(evt)
        self.assert_(evid is None)
        self.assert_(len(self.zem.getHeartbeat()) == 0)
        self.assert_(len(self.zem.getHeartbeat(failures=False)) == 1)


    def testHeartbeatClassTimedOut(self):
        """Test sending heartbeats and the timedout query
        """
        evt = dict(device=TEST_DEVICE, summary='Test', component='Test', 
                    timeout = 0, severity = 5, eventClass="/Heartbeat")
        evid = self.zem.sendEvent(evt)
        self.assert_(evid is None)
        self.assert_(len(self.zem.getHeartbeat()) == 1)
        self.assert_(len(self.zem.getHeartbeat(failures=False)) == 1)


    def testBadClearEvent(self):
        """A Clear message without any previous message"""
        evt = dict(device=TEST_DEVICE, summary='Test', severity=0,
              component="Test", )
        evid = self.zem.sendEvent(evt)
        self.assertNotEquals(evid, None)

    def testBadCharsInEvent(self):
        """Test a message with escapable characters in it. eg ' or " """
        evt = dict(device=TEST_DEVICE, summary='Test', severity=5,
              component="Test'I do bad things with SQL'", )
        evid = self.zem.sendEvent(evt)
        self.assertNotEquals(evid, None)

        evt = dict(device=TEST_DEVICE, summary='Test', severity=5,
              component="Unbalanced single tick ' in message", )
        evt['lastTimeField'] = "Test'I do bad things with SQL'"
        evt['_action'] = "Test'I do bad things with SQL'"
        evid = self.zem.sendEvent(evt)
        self.assertNotEquals(evid, None)

    def testBadCharsInClearEvent(self):
        """Bad chars, but in the clear event"""
        evt = dict(device=TEST_DEVICE, summary='Test', severity=5,
              component="Test'I do bad things with SQL'", )
        evid = self.zem.sendEvent(evt)
        self.assertNotEquals(evid, None)

        from Products.ZenEvents.Event import Event
        clear_evt = Event( **evt )
        clear_evt.severity = 0
        clear_evt.device = "Test'I do bad things with SQL'"
        clear_evt.eventKey = "Test'I do bad things with SQL'"
        clear_evt.evid = "Test'I do bad things with SQL'"
        clear_evt.lastTimeField = "Test'I do bad things with SQL'"
        clear_evt.evil = "Test'I do bad things with SQL'"
        clear_evt._action = "Test'I do bad things with SQL'"
        clear_evt._clearClasses.append( 'evil' )

        # Mess with a backdoor...
        clear_evt._clearClasses.append( clear_evt.evil )
        clear_evid = self.zem.sendEvent(clear_evt)
        self.assertEquals(clear_evid, None)
        
    def testLongComponentIdInClearEvent(self):
        """
        Make sure we handle clear events for components with
        ids > 255 chars
        """
        longComponentId = "X" * 275
        testEventKey = 'longComponentClearEventKey'
        evt = dict(device=TEST_DEVICE, summary='Test', severity=5,
              component=longComponentId, eventKey=testEventKey,
              eventClass='Device' )
        evid = self.zem.sendEvent(evt)
        self.assertNotEquals(evid, None)

        from Products.ZenEvents.Event import Event
        clear_evt = Event( **evt )
        clear_evt.severity = 0
        clear_id = self.zem.sendEvent(clear_evt)
        
        extraField=('clearid',)
        statusEvents = self.zem.getEventList(where="evid='%s'" % evid,
                                             resultFields=extraField)
        self.assertEquals( len( statusEvents ), 0 )
        historyEvents = self.dmd.ZenEventHistory.getEventList(
                                            where="evid='%s'" % evid,
                                            resultFields=extraField)
        self.assertEquals( len( historyEvents ), 1 )
        self.assertEquals( historyEvents[0].clearid, clear_id )
    
    def testHierarchicalTransforms(self):
        """
        Are transforms applied down the event class tree properly?
        """
        e = self.dmd.Events
        e.createOrganizer('/LevelOne/LevelTwo')
        e.LevelOne.transform = "evt.severity = 1\n"
        e.LevelOne.transform += "evt.levels = 'one'\n"
        e.LevelOne.LevelTwo.transform = "evt.severity = 2\n"
        e.LevelOne.LevelTwo.transform += "evt.levels += ',two'\n"
        
        mapping = e.LevelOne.LevelTwo.createInstance("testMapping")
        mapping.eventClassKey = "testMappingKey"
        mapping.sequence = 0
        mapping.transform = "evt.severity = 3\n"
        mapping.transform += "evt.levels += ',three'\n"
        mapping.index_object()
        
        evt = dict(device=TEST_DEVICE, summary="hierarchical transform test",
            severity=5, eventKey="testOne", eventClass="/LevelOne")
        evid = self.zem.sendEvent(evt)
        evt_p = self.zem.getEventDetailFromStatusOrHistory(evid)
        self.assertEquals(evt_p.severity, 1)
        self.assertEquals(evt_p._details[0][1], "one")

        evt = dict(device=TEST_DEVICE, summary="hierarchical transform test",
            severity=5, eventKey="testTwo", eventClass="/LevelOne/LevelTwo")
        evid = self.zem.sendEvent(evt)
        evt_p = self.zem.getEventDetailFromStatusOrHistory(evid)
        self.assertEquals(evt_p.severity, 2)
        self.assertEquals(evt_p._details[0][1], "one,two")

        evt = dict(device=TEST_DEVICE, summary="hierarchical transform test",
            severity=5, eventKey="testThree", eventClassKey="testMappingKey")
        evid = self.zem.sendEvent(evt)
        evt_p = self.zem.getEventDetailFromStatusOrHistory(evid)
        self.assertEquals(evt_p.severity, 3)
        self.assertEquals(evt_p._details[0][1], "one,two,three")


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(MySqlSendEventTest))
    return suite
