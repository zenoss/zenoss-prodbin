##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenEvents.SyslogProcessing import SyslogProcessor
from Products.ZenTestCase.BaseTestCase import BaseTestCase

class SyslogProcessingTest(BaseTestCase):

    def sendEvent(self, evt):
        "Fakeout sendEvent() method"
        self.sent = evt

    def testBuildEventClassKey(self):
        "Simple, brain-dead testing of SyslogProcessor"
        base = dict(device='localhost', component='component', severity=3)
        s = SyslogProcessor(self.sendEvent, 6, False, 'localhost', 3)
        self.assert_(s.buildEventClassKey({}) == {})
        evt = dict(eventClassKey='akey', **base)
        self.assert_(s.buildEventClassKey(evt.copy()) == evt)
        evt = dict(eventClassKey='akey', ntevid='1234', **base)
        self.assert_(s.buildEventClassKey(evt.copy()) == evt)
        evt = dict(ntevid='1234', **base)
        self.assert_(s.buildEventClassKey(evt)['eventClassKey'] ==
                     'component_1234')
        evt = dict(**base)
        self.assert_(s.buildEventClassKey(evt)['eventClassKey'] == 'component')

    def testCheckFortigate(self):
        """
        Test of Fortigate syslog message parsing
        """
        msg = "date=xxxx devname=blue log_id=987654321 type=myComponent blah blah blah"
        s = SyslogProcessor(self.sendEvent, 6, False, 'localhost', 3)
        evt = s.parseTag( {}, msg )

        self.assertEquals( evt.get('eventClassKey'), '987654321' )
        self.assertEquals( evt.get('component'), 'myComponent' )
        self.assertEquals( evt.get('summary'), 'devname=blue log_id=987654321 type=myComponent blah blah blah' )

    def testCheckCiscoPortStatus(self):
        """
        Test of Cisco port status syslog message parsing
        """
        msg = "Process 10532, Nbr 192.168.10.13 on GigabitEthernet2/15 from LOADING to FULL, Loading Done"
        s = SyslogProcessor(self.sendEvent, 6, False, 'localhost', 3)
        evt = s.parseTag( {}, msg )

        self.assertEquals( evt.get('device'), '192.168.10.13' )
        self.assertEquals( evt.get('process_id'), '10532' )
        self.assertEquals( evt.get('interface'), 'GigabitEthernet2/15' )
        self.assertEquals( evt.get('start_state'), 'LOADING' )
        self.assertEquals( evt.get('end_state'), 'FULL' )
        self.assertEquals( evt.get('summary'), 'Loading Done')
    
    def testCiscoVpnConcentrator(self):
        """
        Test of Cisco VPN Concentrator syslog message parsing
        """
        msg = "54884 05/25/2009 13:41:14.060 SEV=3 HTTP/42 RPT=4623 Error on socket accept."
        s = SyslogProcessor(self.sendEvent, 6, False, 'localhost', 3)
        evt = s.parseTag( {}, msg )
        
        self.assertEquals( evt.get('eventClassKey'), 'HTTP/42' )
        self.assertEquals( evt.get('summary'), 'Error on socket accept.' )

    def testCiscoStandardMessageSeverity(self):
        """
        Test that the event severity is correctly extracted from the
        Cisco standard message body
        """
        msg = '2014 Jan 31 19:45:51 R2-N6K1-2010-P1 %ETH_PORT_CHANNEL-5-CREATED: port-channel1 created'
        s = SyslogProcessor(self.sendEvent, 6, False, 'localhost', 3)
        evt = s.parseTag( {}, msg )
        self.assertEquals( evt.get('overwriteSeverity'), '5' )

    def testDellSyslog(self):
        """
        Test dell stuf
        """
        msg = ("1-Oct-2009 23:00:00.383809:snapshotDelete.cc:290:INFO:8.2.5:Successfully deleted snapshot 'UNVSQLCLUSTERTEMPDB-2009-09-30-23:00:14.11563'.")
        s = SyslogProcessor(self.sendEvent, 6, False, 'localhost', 3)
        evt = s.parseTag( {}, msg )
        
        self.assertEquals( evt.get('eventClassKey'), '8.2.5' )
        self.assertEquals( evt.get('summary'), 
                           "Successfully deleted snapshot 'UNVSQLCLUSTERTEMPDB-2009-09-30-23:00:14.11563'.")
        
    def testDellSyslog2(self):
        """
        Test dell stuf
        """
        msg = ("2626:48:VolExec:27-Aug-2009 13:15:58.072049:VE_VolSetWorker.hh:75:WARNING:43.3.2:Volume volumeName has reached 96 percent of its reported size and is currently using 492690MB.")
        s = SyslogProcessor(self.sendEvent, 6, False, 'localhost', 3)
        evt = s.parseTag( {}, msg )
        
        self.assertEquals( evt.get('eventClassKey'), '43.3.2' )
        self.assertEquals( evt.get('summary'), 
                           "Volume volumeName has reached 96 percent of its reported size and is currently using 492690MB.")

    def testNetAppSyslogParser(self):
        """
        Test NetApp syslog parser.
        """
        msg = '[deviceName: 10/100/1000/e1a:warning]: Client 10.0.0.101 (xid 4251521131) is trying to access an unexported mount (fileid 64, snapid 0, generation 6111516 and flags 0x0 on volume 0xc97d89a [No volume name available])'
        s = SyslogProcessor(self.sendEvent, 6, False, 'localhost', 3)
        evt = s.parseTag({}, msg)
        self.assertEquals(evt.get('component'), '10/100/1000/e1a')
        self.assertEquals(evt.get('summary'), 'Client 10.0.0.101 (xid 4251521131) is trying to access an unexported mount (fileid 64, snapid 0, generation 6111516 and flags 0x0 on volume 0xc97d89a [No volume name available])')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(SyslogProcessingTest))
    return suite
