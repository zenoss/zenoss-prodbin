###############################################################################
#
#   Copyright (c) 2004 Zentinel Systems. 
#
#   This library is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
###############################################################################


import unittest
import os
from os import path

from ZenEvents.EventManager import EventManager, EventUpdateError, defaultPickleName
from ZenEvents.Event import Event

class testEventManager(unittest.TestCase):
  
    loopsize = 100

    def setUp(self):
        self.zem = EventManager()
        for i in range(self.loopsize):
            self.zem.addevent(Event("conrad.confmon.loc", 
                                summary="this is a test", severity=5))


    def tearDown(self):
        if path.exists(defaultPickleName):
            os.remove(defaultPickleName)    
        self.zem = None

    def testGetFields(self):
        """kind of bogus test to see if get fields is working"""
        ev = Event("sdf")
        import pdb
        pdb.set_trace()
        self.failUnless(len(ev.getfields()) == 8)
    
    def testAddEvents(self):
        self.failUnless(len(self.zem.getevents()) == self.loopsize)
   
    def testAddEventDict(self):
        oid = self.zem.addevent({"device":"pageup", 
                    "summary": "dict event", "severity":30})
        ev = self.zem.getevent(oid)
        self.failUnless(ev.device == 'pageup' and 
                        ev.summary == 'dict event' and ev.severity == 30)

    def testGetEvent(self):
        ev1 = self.zem.getevent(65)
        self.failUnless(ev1._oid == 65)
        ev2 = self.zem.getevent(65)
        self.failUnless(ev1.serial == ev2.serial)
        self.failIf(id(ev1) == id(ev2))


    def testSaveAndLoadEvents(self):
        self.zem.saveevents()
        self.zem.loadevents()
        self.failUnless(len(self.zem.getevents()) == self.loopsize)

    def testNextOid(self):
        """make sure nextoid is correct after reload from disk"""
        self.zem.saveevents()
        self.zem.loadevents()
        self.zem.addevent(Event("xyz.confmon.loc", summary="test event"))
        ev = self.zem.getDeviceEvents("xyz.confmon.loc")[0]
        self.failIf(ev._oid == 0)
        self.failUnless(ev.summary == "test event")


    def testFilterEvents(self):
        self.zem.addevent(Event("conrad.confmon.loc", summary="test event"))
        evts = self.zem.getevents(lambda x: x.summary == "test event")
        self.failUnless(len(evts) == 1)

    
    def testDeviceEvents(self):
        self.zem.addevent(Event("pageup.confmon.loc", summary="test event"))
        self.failUnless(
            len(self.zem.getDeviceEvents("pageup.confmon.loc")) == 1)


    def testUpdateEvent(self):
        oid = self.zem.addevent(
            Event("pageup.confmon.loc", summary="test event"))
        ev = self.zem.getevent(oid)
        evserial = ev.serial
        ev.summary = "new summary"
        self.zem.updateevent(ev)
        nev = self.zem.getevent(oid)
        self.failUnless(nev.serial == (evserial + 1))
        self.failUnless(nev.summary == "new summary")

    def testUpdateConflict(self):
        oid = self.zem.addevent(
            Event("pageup.confmon.loc", summary="test event"))
        ev1 = self.zem.getevent(oid)
        ev2 = self.zem.getevent(oid)
        ev2.summary="ev2 version"
        ev1.summary="ev1 version"
        self.zem.updateevent(ev2)
        self.failUnlessRaises(EventUpdateError, self.zem.updateevent, ev1)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest( unittest.makeSuite( testEventManager ) )
    return suite


if __name__ == "__main__":
    unittest.main()
