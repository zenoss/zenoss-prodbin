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

from ZenEvents.EventManager import EventManager, defaultPickleName
from ZenEvents.Event import Event

class testEventManager(unittest.TestCase):
  
    loopsize = 10000

    def setUp(self):
        self.zem = EventManager()


    def tearDown(self):
        if path.exists(defaultPickleName):
            os.remove(defaultPickleName)    
        self.zem = None


    def testAddEvents(self):
        for i in range(self.loopsize):
            self.zem.addevent(Event(i))
        self.failUnless(len(self.zem.getevents()) == self.loopsize)
    

    def testAddEvents(self):
        for i in range(self.loopsize):
            self.zem.addevent(Event(i))
        ev = self.zem.getevent(65)
        self.failUnless(ev.oid == 65)


    def testSaveAndLoadEvents(self):
        for i in range(self.loopsize):
            self.zem.addevent(Event(i))
        self.zem.saveevents()
        self.zem.loadevents()
        self.failUnless(len(self.zem.getevents()) == self.loopsize)


    def testFilterEvents(self):
        for i in range(self.loopsize):
            self.zem.addevent(Event(i, summary=i))
        self.failUnless(len(self.zem.getevents(lambda x: x.summary == 10)) == 1)

    
    def testDeviceEvents(self):
        for i in range(self.loopsize):
            self.zem.addevent(Event(i))
        self.failUnless(len(self.zem.getDeviceEvents(24)) == 1)



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest( unittest.makeSuite( testEventManager ) )
    return suite


if __name__ == "__main__":
    unittest.main()
