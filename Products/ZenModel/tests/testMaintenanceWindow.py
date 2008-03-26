###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.MaintenanceWindow import MaintenanceWindow, DAY_SECONDS
import time

class TestMaintenanceWindows(ZenModelBaseTest):

    def testProductionStateIndexing(self):
        mwid = 'testwindow1'
        devid = 'unittestdevice1'
        grpid = 'unittestGroup'
        grp = self.dmd.Groups.createOrganizer(grpid)
        dev = self.dmd.Devices.createInstance(devid)
        dev.setGroups(grp.id)
        grp.manage_addMaintenanceWindow(mwid)
        mw = grp.maintenanceWindows._getOb(mwid)
        mw.begin()
        self.assert_(dev.productionState==mw.startProductionState)
        prodstate = dev.getProdState()
        catalog = self.dmd.Devices.deviceSearch
        results = [x.id for x in catalog(getProdState=prodstate)]
        self.assert_(dev.id in results)

    def testMaintenanceWindows(self):
        m = MaintenanceWindow('tester')
        t = time.mktime( (2006, 1, 29, 10, 45, 12, 6, 29, 0) )
        P = 60*60*2
        m.set(t, P, m.NEVER)
        self.assert_(m.next() == None)
        m.set(t, P, m.DAILY)
        c = time.mktime( (2006, 1, 30, 10, 45, 12, 6, 29, 0) )
        self.assert_(m.next(t + P + 1) == c)
        m.set(t, P, m.WEEKLY)
        c = time.mktime( (2006, 2, 5, 10, 45, 12, 6, 36, 0) )
        self.assert_(m.next(t + 1) == c)
        m.set(t - DAY_SECONDS, P, m.EVERY_WEEKDAY)
        c = time.mktime( (2006, 1, 30, 10, 45, 12, 7, 30, 0) )
        self.assert_(m.next(t) == c)
        m.set(t, P, m.MONTHLY)
        c = time.mktime( (2006, 2, 28, 10, 45, 12, 0, 0, 0) )
        self.assert_(m.next(t+1) == c)
        t2 = time.mktime( (2005, 12, 31, 10, 45, 12, 0, 0, 0) )
        m.set(t2, P, m.MONTHLY)
        c = time.mktime( (2006, 1, 31, 10, 45, 12, 0, 0, 0) )
        c2 = time.mktime( (2006, 2, 28, 10, 45, 12, 0, 0, 0) )
        self.assert_(m.next(t2+1) == c)
        self.assert_(m.next(c+1) == c2)
        c = time.mktime( (2006, 2, 5, 10, 45, 12, 0, 0, 0) )
        m.set(t, P, m.FSOTM)
        self.assert_(m.next(t+1) == c)

        # skips
        m.skip = 2
        m.set(t, P, m.DAILY)
        c = time.mktime( (2006, 1, 31, 10, 45, 12, 6, 29, 0) )
        self.assert_(m.next(t + 1) == c)

        m.set(t, P, m.WEEKLY)
        c = time.mktime( (2006, 2, 12, 10, 45, 12, 6, 36, 0) )
        self.assert_(m.next(t + 1) == c)

        m.set(t, P, m.MONTHLY)
        c = time.mktime( (2006, 3, 29, 10, 45, 12, 6, 36, 0) )
        self.assert_(m.next(t + 1) == c)

        m.set(t - DAY_SECONDS * 2, P, m.EVERY_WEEKDAY)
        c = time.mktime( (2006, 1, 31, 10, 45, 12, 7, 30, 0) )
        self.assert_(m.next(t + 1) == c)

        c = time.mktime( (2006, 3, 5, 10, 45, 12, 0, 0, 0) )
        m.set(t, P, m.FSOTM)
        self.assert_(m.next(t+1) == c)

        m1 = MaintenanceWindow('t1')
        m2 = MaintenanceWindow('t2')
        t = time.mktime( (2006, 1, 29, 10, 45, 12, 6, 29, 0) )
        duration = 1
        m1.set(t, duration, m.NEVER)
        m2.set(t + duration * 60, duration, m.NEVER)
        m1.started = t
        # ending of m1 should be < start of m2
        self.assert_(m1.nextEvent(t + 1) < m2.nextEvent(t + 1))

        from Products.ZenUtils.FakeRequest import FakeRequest
        r = FakeRequest()
        m.manage_editMaintenanceWindow(
                                         startDate='01/29/2006',
                                         startHours='10',
                                         startMinutes='45',
                                         durationDays='1',
                                         durationHours='1',
                                         durationMinutes='1',
                                         repeat='Weekly',
                                         startProductionState=300,
                                         stopProductionState=-99,
                                         enabled=True,
                                         REQUEST=r)

        self.assert_(r.has_key('message'))
        self.assert_(r['message'] == 'Saved Changes')
        self.assert_(m.start == t - 12)
        self.assert_(m.duration == 24*60+61)
        self.assert_(m.repeat == 'Weekly')
        self.assert_(m.startProductionState == 300)
        self.assert_(m.stopProductionState == -99)

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestMaintenanceWindows))
    return suite

