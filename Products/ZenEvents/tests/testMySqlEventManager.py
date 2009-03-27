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

import unittest
import Globals
import transaction

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenEvents.Event import Event
from Products.ZenEvents.Exceptions import *

class MySqlEventManagerTest(BaseTestCase):
    """
    To run these tests zport.dmd.ZenEventManager must exist and must be setup
    with a proper config to access the mysql backend.  MySQL must also have
    an events database created with bin/zeneventbuild.
    Zeo must be running.
    """

    def setUp(self):
        BaseTestCase.setUp(self)
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
        self.zem = None
        BaseTestCase.tearDown(self)

    
    def testSendEvent(self):
        self.zem.sendEvent(self.evt)
        evts = self.zem.getEventList(where="device='%s'" % self.evt.device)
        self.assertEqual(len(evts), 1)
        self.assertEqual(evts[0].summary, self.evt.summary)


    def testSendEventDup(self):
        self.zem.sendEvent(self.evt.__dict__)
        self.zem.sendEvent(self.evt.__dict__) 
        evts = self.zem.getEventList(where="device='%s'" % self.evt.device)
        self.assertEqual(len(evts), 1)
        self.assertEqual(evts[0].count, 2)


    def testEventMissingRequired(self):
        delattr(self.evt, "device")
        self.assertRaises(ZenEventError, self.zem.sendEvent, self.evt) 


    def testEventDetailField(self):
        self.evt.test = "Error"
        evt = self.zem.sendEvent(self.evt)
        evdetail = self.zem.getEventDetail(dedupid=self.evt.dedupid)
        self.assert_(("test", self.evt.test) in 
                        evdetail.getEventDetails())

    
    def testEventDetailFields(self):
        self.evt.ntseverity = "Error"
        self.evt.ntsource = "Zope"
        self.evt.foo = "Bar"
        evt = self.zem.sendEvent(self.evt)
        evdetail = self.zem.getEventDetail(evt)
        details = evdetail.getEventDetails()
        self.assert_(("ntseverity", self.evt.ntseverity) in details)
        self.assert_(("ntsource", self.evt.ntsource) in details)
        self.assert_(("foo", self.evt.foo) in details)
    
    
    def testEventDetailgetEventFields(self):
        evt = self.zem.sendEvent(self.evt)
        evdetail = self.zem.getEventDetail(dedupid=self.evt.dedupid)
        feilds = evdetail.getEventFields()


    def testMoveEventToHistory(self):
        # NB: when we delete an event, the MySQL DB trigger moves 
        #     the event to the 'history' table
        evid= self.zem.sendEvent(self.evt) 
        evts = self.zem.getEventList(where="device='%s'" % self.evt.device)
        self.assertEqual(len(evts), 1)
        self.assertEqual(evts[0].evid, evid )
        self.assertEqual(evts[0].summary, self.evt.summary)

        # Now move the event to history
        self.dmd.ZenEventManager.manage_deleteEvents( evid )
        evts = self.zem.getEventList(where="device='%s'" % self.evt.device)
        self.assertEqual(len(evts), 0)

        self.assertRaises( ZenEventNotFound, self.dmd.ZenEventManager.getEventDetail, evid )

        try:
            event = self.dmd.ZenEventHistory.getEventDetail( evid )
        except ZenEventNotFound:
            self.fail( "Unable to find evid %s in database after moving to history" % evid )

        self.assert_( event is not None )
        self.assertEqual(event.evid, evid )

    
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(MySqlEventManagerTest))
    return suite


