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
from Queue import Queue
import Globals
import transaction

from Products.ZenUtils.ZCmdBase import ZCmdBase
zodb = ZCmdBase(noopts=True)

from Products.ZenEvents.MySqlSendEvent import MySqlSendEventThread 
from Products.ZenEvents.Event import Event
from Products.ZenEvents.Exceptions import *

class MySqlSendEventThreadTest(unittest.TestCase):
    
    def setUp(self):
        zodb.getDataRoot()
        self.zem = zodb.dmd.ZenEventManager


    def tearDown(self):
        transaction.abort()
        zem = self.dmd.ZenEventManager
        conn = zem.connect()
        try:
            curs = conn.cursor()
            zem.curs.execute("truncate status")
        finally: zem.close(conn)
        zodb.closedb()
        self.zem = None


    def testInit(self):
        evthread = MySqlSendEventThread(self.zem)
        self.assert_(evthread.database == "127.0.0.1")
        self.assert_(evthread.detailTable == "detail")
        self.assert_(isinstance(evthread.getqueue(), Queue)) 
        

    def testSendEvent(self):
        evthread = MySqlSendEventThread(self.zem)
        queue = evthread.getqueue()
        evt = Event()
        evt.device = "dev.test.com"
        evt.eventClass = "TestEvent"
        evt.summary = "this is a test event"
        evt.severity = 3
        queue.put(evt)
        evthread.stop()
        evthread.run()
        evts = self.zem.getEventList(where="device='dev.test.com'")
        self.assert_(len(evts) == 1)
        self.assert_(evts[0].summary == evt.summary)

        

if __name__ == "__main__":
    unittest.main()


