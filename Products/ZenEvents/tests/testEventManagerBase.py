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
import md5
import os

from Products.ZenEvents.Event import Event
from Products.ZenTestCase.ZenTestCase import ZenTestCase

getuid = lambda:md5.md5(os.urandom(10)).hexdigest()[:8]

class testEventManagerBase(ZenTestCase):
    
    def setUp(self):
        self.zem = self.dmd.ZenEventManager
        self.sqlconn = self.zem.connect()
        cursor = self.sqlconn.cursor()
        self.execute = lambda query:cursor.execute(query)

    def tearDown(self):
        try:
            self.execute("TRUNCATE status;")
            self.execute("TRUNCATE detail;")
            self.execute("TRUNCATE log;")
            self.execute("TRUNCATE history;")
        finally: 
            self.zem.close(self.sqlconn)

    def getDevice(self):
        devid = dmd.Devices.getUnusedId('devices', 'testdev')
        return dmd.Devices.createInstance(devid)
        
    def sendEvent(self, devid):
        evt = Event()
        evt.device = devid
        evt.eventClass = "Test"
        evt.summary = "This is a test. UID: %s" % getuid()
        evt.severity = 5
        return self.zem.sendEvent(evt)

    def test_getEventListME(self):
        d = self.getDevice()
        evid = self.sendEvent(d.id)
        evs = self.zem.getEventListME(d)
        self.assert_(len(evs)==1)
        self.assert_(evid in [ev.evid for ev in evs])

    def test_getEventBatchME(self):
        pass


def test_suite():
    return unittest.makeSuite(testEventManagerBase)


