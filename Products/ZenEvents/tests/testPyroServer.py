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
import Pyro.core
from ZenEvents.Event import Event

class testPyroServer(unittest.TestCase):
    
    loopsize = 1000
    
    def setUp(self):
        self.zes = Pyro.core.getProxyForURI(
                        "PYROLOC://localhost:7766/EventServer")
        self.zdb = Pyro.core.getProxyForURI(self.zes.openDatabase('zentinel'))

    def tearDown(self):
        self.zdb.deleteevents()
        self.zes.closeDatabase('zentinel')
        self.zes = None

    def testAddEvents(self):
        for i in range(self.loopsize):
            self.zdb.addevent(Event("conrad.confmon.loc", 
                                summary="this is a event %d" % i, severity=5))
        self.failUnless(len(self.zdb.getevents()) == self.loopsize)
  
    def testAddEventsOneway(self):
        self.zdb._setOneway('addevent')
        for i in range(self.loopsize):
            self.zdb.addevent(Event("conrad.confmon.loc", 
                                summary="this is a event %d" % i, severity=5))
        self.failUnless(len(self.zdb.getevents()) == self.loopsize)

if __name__ == "__main__":
    Pyro.core.initClient(0)
    unittest.main()
