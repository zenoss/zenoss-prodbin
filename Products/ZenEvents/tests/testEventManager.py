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
import pdb
import pickle
import os
from os import path

from Products.ZenEvents.EventDatabase import EventDatabase, EventUpdateError
from Products.ZenEvents.EventDatabase import defaultPickleName
from Products.ZenEvents.Event import Event

class testEventDatabase(unittest.TestCase):
  
    loopsize = 100
    journalName = defaultPickleName + ".jnl"

    def setUp(self):
        self.cleanup()
        self.zem = EventDatabase(savetime=0,journal=True)
        for i in range(self.loopsize):
            self.zem.addevent(Event("conrad.confmon.loc", 
                                summary="this is a event %05d" % i, severity=5))


    def tearDown(self):
        self.zem = None
        self.cleanup()

    def cleanup(self):
        if path.exists(defaultPickleName):
            os.remove(defaultPickleName)    
        if path.exists(self.journalName):
            os.remove(self.journalName)    

    def testGetFields(self):
        """kind of bogus test to see if get fields is working"""
        ev = Event("sdf")
        self.failUnless(len(ev.getfields()) == 10)
    
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
        self.failUnless(ev1._serial == ev2._serial)
        self.failIf(id(ev1) == id(ev2))


    def testSaveAndLoadEvents(self):
        if self.zem.journal:
            i = 0
            jf = open(self.journalName, "r")
            while 1:
                try:
                    pickle.load(jf)
                    i += 1
                except EOFError: break
            self.failUnless(i == self.loopsize)
        self.zem.saveevents()
        #self.failIf(path.exists(self.journalName))
        self.zem.loadevents()
        self.failUnless(len(self.zem.getevents()) == self.loopsize)


    def testRecoverFromJournal(self):
        """recover the database from the journal file after failure"""
        if self.zem.journal:
            self.zem = None
            self.zem = EventDatabase(savetime=0)
            self.failUnless(len(self.zem.getevents()) == self.loopsize)

        
    def testNextOid(self):
        """make sure nextoid is correct after reload from disk"""
        self.zem.saveevents()
        self.zem.loadevents()
        self.zem.addevent(Event("xyz.confmon.loc", summary="test event"))
        ev = self.zem.getDeviceEvents("xyz.confmon.loc")[0]
        self.failIf(ev._oid == 0)
        self.failUnless(ev.summary == "test event")


    def testDeleteAllEvents(self):
        self.zem.deleteevents()
        self.failUnless(len(self.zem.getevents()) == 0)

    def testDeleteSomeEvents(self):
        self.zem.deleteevents(lambda x: '00008' in x.summary 
                                or '00009' in x.summary)
        self.failUnless(len(self.zem.getevents()) == (self.loopsize - 2))

    def testDeleteByOid(self):
        self.zem.deleteevent(4)
        self.failUnless(len(self.zem.getevents()) == (self.loopsize - 1))


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
        evserial = ev._serial
        ev.summary = "new summary"
        self.zem.updateevent(ev)
        nev = self.zem.getevent(oid)
        self.failUnless(nev._serial == (evserial + 1))
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

    def testGetEvents(self):
        """test to make sure that lambda string query works"""
        evts = self.zem.getEvents("'00009' in ev.summary")
        self.failUnless(len(evts) == 1)

    def testBadLambdaStr(self):
        self.failUnlessRaises(NameError, 
            self.zem.getEvents, "'00009' in xyz.summary")
         

    def testGetDeviceEvents(self):
        evts = self.zem.getDeviceEvents("conrad.confmon.loc")
        self.failUnless(len(evts) == self.loopsize)

    def testGetRegexEvents(self):
        evts = self.zem.getRegexEvents("00009")
        self.failUnless(len(evts) == 1) 
        
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest( unittest.makeSuite( testEventDatabase ) )
    return suite


if __name__ == "__main__":
    unittest.main()
