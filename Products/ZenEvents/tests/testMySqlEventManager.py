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
import pdb
import unittest
import Globals
import transaction

from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenEvents.Event import Event
from Products.ZenEvents.Exceptions import *

zodb = ZCmdBase(noopts=True)

class MySqlEventMangerTest(unittest.TestCase):
    """
    To run these tests zport.dmd.ZenEventManager must exist and must be setup
    with a proper config to access the mysql backend.  MySQL must also have
    an events database created with bin/zeneventbuild.
    Zeo must be running.
    """

    def setUp(self):
        zodb.getDataRoot()
        self.dmd = zodb.dmd
        self.zem = self.dmd.ZenEventManager
        self.evt = Event()
        self.evt.device = "dev.test.com"
        self.evt.eventClass = "TestEvent"
        self.evt.summary = "this is a test event"
        self.evt.severity = 3

    def tearDown(self):
        transaction.abort()
        zem = self.dmd.ZenEventManager
        conn = zem.connect()
        try:
            curs = conn.cursor()
            curs.execute("truncate status")
            curs.execute("truncate detail")
            curs.execute("truncate log")
            curs.execute("truncate history")
        finally: zem.close(conn)
        zodb.closedb()
        self.dmd = None
        self.zem = None

    
    def testSendEvent(self):
        self.zem.sendEvent(self.evt) 
        evts = self.zem.getEventList(where="device='dev.test.com'")
        self.assert_(len(evts) == 1)
        self.assert_(evts[0].summary == self.evt.summary)


    def testSendEventDup(self):
        self.zem.sendEvent(self.evt) 
        self.zem.sendEvent(self.evt) 
        evts = self.zem.getEventList(where="device='dev.test.com'")
        self.assert_(len(evts) == 1)
        self.assert_(evts[0].count == 2)


    def testEventMissingRequired(self):
        delattr(self.evt, "eventClass")
        self.assertRaises(ZenEventError, self.zem.sendEvent, self.evt) 


    def testEventDetailField(self):
        self.evt.ntseverity = "Error"
        evt = self.zem.sendEvent(self.evt)
        evdetail = self.zem.getEventDetail(dedupid=evt.dedupid)
        self.assert_(("ntseverity", self.evt.ntseverity) in 
                        evdetail.getEventDetails())

    
    def testEventDetailFields(self):
        self.evt.ntseverity = "Error"
        self.evt.ntsource = "Zope"
        evt = self.zem.sendEvent(self.evt)
        evdetail = self.zem.getEventDetail(dedupid=evt.dedupid)
        details = evdetail.getEventDetails()
        self.assert_(("ntseverity", self.evt.ntseverity) in details)
        self.assert_(("ntsource", self.evt.ntsource) in details)
    
    
    def testEventDetailgetEventFields(self):
        evt = self.zem.sendEvent(self.evt)
        evdetail = self.zem.getEventDetail(dedupid=evt.dedupid)
        feilds = evdetail.getEventFields()

    

if __name__ == "__main__":
    unittest.main()


