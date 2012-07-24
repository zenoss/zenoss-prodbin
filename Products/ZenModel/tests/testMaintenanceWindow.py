##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from time import mktime, time

from ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.MaintenanceWindow import MaintenanceWindow, DAY_SECONDS
# Note: The new messaging code inteferes with FakeRequest operations,
#      as the adapter machinery doesn't load
#from Products.ZenUtils.FakeRequest import FakeRequest


# Note: These defaults can be overridden by the user, but we only need an
#       example set to test.
state_Production=1000
state_Pre_Production=500
state_Test=400
state_Maintenance=300
state_Decommissioned=-1

stateNames = {
    state_Production:'Production',
    state_Pre_Production:'Pre-Production',
    state_Test:'Test',
    state_Maintenance:'Mainetenance',
    state_Decommissioned:'Decommissioned',
}

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
        mw.enabled = True
        mw.begin()
        self.assert_(dev.productionState==mw.startProductionState)
        prodstate = dev.getProdState()
        catalog = self.dmd.Devices.deviceSearch
        results = [x.id for x in catalog(getProdState=prodstate)]
        self.assert_(dev.id in results)

    def testMaintenanceWindows(self):
        m = MaintenanceWindow('tester')
        t = mktime( (2006, 1, 29, 10, 45, 12, 6, 29, 0) )
        P = 60*60*2
        # set(start, duration, repeat, enabled=True)
        m.set(t, P, m.NEVER)
        self.assert_(m.next() == None)
        m.set(t, P, m.DAILY)
        c = mktime( (2006, 1, 30, 10, 45, 12, 6, 29, 0) )
        self.assert_(m.next(t + P + 1) == c)
        m.set(t, P, m.WEEKLY)
        c = mktime( (2006, 2, 5, 10, 45, 12, 6, 36, 0) )
        self.assert_(m.next(t + 1) == c)
        m.set(t - DAY_SECONDS, P, m.EVERY_WEEKDAY)
        c = mktime( (2006, 1, 30, 10, 45, 12, 7, 30, 0) )
        self.assert_(m.next(t) == c)
        m.set(t, P, m.MONTHLY)
        c = mktime( (2006, 2, 28, 10, 45, 12, 0, 0, 0) )
        self.assert_(m.next(t+1) == c)
        t2 = mktime( (2005, 12, 31, 10, 45, 12, 0, 0, 0) )
        m.set(t2, P, m.MONTHLY)
        c = mktime( (2006, 1, 31, 10, 45, 12, 0, 0, 0) )
        c2 = mktime( (2006, 2, 28, 10, 45, 12, 0, 0, 0) )
        self.assert_(m.next(t2+1) == c)
        self.assert_(m.next(c+1) == c2)
        c = mktime( (2006, 2, 5, 10, 45, 12, 0, 0, 0) )
        m.set(t, P, m.FSOTM)
        self.assert_(m.next(t+1) == c)

        # DST
        FSOTM_Map = {
            # DST day      following first sunday of the month
            (2008, 3, 9):  (2008, 4, 6),
            (2008, 11, 2): (2008, 12, 7),
            }
        for (yy, mm, dd), sunday in FSOTM_Map.items():
            duration = 3*60
            tt = mktime( (yy, mm, dd, 12, 10, 9, 0, 0, -1) )
            m.set(tt, duration, m.DAILY)
            c = mktime( (yy, mm, dd + 1, 12, 10, 9, 0, 0, -1) )
            self.assert_(m.next(tt + duration) == c)

            m.set(tt, duration, m.WEEKLY)
            c = mktime( (yy, mm, dd + 7, 12, 10, 9, 0, 0, -1) )
            self.assert_(m.next(tt + duration) == c)

            m.set(tt, duration, m.EVERY_WEEKDAY)
            c = mktime( (yy, mm, dd + 1, 12, 10, 9, 0, 0, -1) )
            self.assert_(m.next(tt + duration) == c)

            m.set(tt, duration, m.FSOTM)
            c = mktime( sunday + (12, 10, 9, 0, 0, -1) )
            self.assert_(m.next(tt + duration) == c)

            # DST: check that a 3-hour range ends at the proper time
            tt = mktime( (yy, mm, dd, 0, 10, 9, 0, 0, -1) )
            m.set(tt, duration, m.DAILY)
            m.started = tt
            c = mktime( (yy, mm, dd, 3, 10, 8, 0, 0, -1) )
            self.assert_(m.nextEvent(tt) == c)
            m.started = None

        # skips
        m.skip = 2
        m.set(t, P, m.DAILY)
        c = mktime( (2006, 1, 31, 10, 45, 12, 6, 29, 0) )
        self.assert_(m.next(t + 1) == c)

        m.set(t, P, m.WEEKLY)
        c = mktime( (2006, 2, 12, 10, 45, 12, 6, 36, 0) )
        self.assert_(m.next(t + 1) == c)

        m.set(t, P, m.MONTHLY)
        c = mktime( (2006, 3, 29, 10, 45, 12, 6, 36, 0) )
        self.assert_(m.next(t + 1) == c)

        m.set(t - DAY_SECONDS * 2, P, m.EVERY_WEEKDAY)
        c = mktime( (2006, 1, 31, 10, 45, 12, 7, 30, 0) )
        self.assert_(m.next(t + 1) == c)

        c = mktime( (2006, 3, 5, 10, 45, 12, 0, 0, 0) )
        m.set(t, P, m.FSOTM)
        self.assert_(m.next(t+1) == c)

        m1 = MaintenanceWindow('t1')
        m2 = MaintenanceWindow('t2')
        t = mktime( (2006, 1, 29, 10, 45, 12, 6, 29, 0) )
        duration = 1
        m1.set(t, duration, m.NEVER)
        m2.set(t + duration * 60, duration, m.NEVER)
        m1.started = t
        # ending of m1 should be < start of m2
        self.assert_(m1.nextEvent(t + 1) < m2.nextEvent(t + 1))

        #r = FakeRequest()
        r = None
        m.manage_editMaintenanceWindow(
                                         startDate='01/29/2006',
                                         startHours='10',
                                         startMinutes='45',
                                         durationDays='1',
                                         durationHours='1',
                                         durationMinutes='1',
                                         repeat='Weekly',
                                         startProductionState=state_Maintenance,
                                         enabled=True,
                                         REQUEST=r)

        #self.assert_('message' in r)
        #self.assert_(r['message'] == 'Saved Changes')
        self.assert_(m.start == t - 12)
        self.assert_(m.duration == 24*60+61)
        self.assert_(m.repeat == 'Weekly')
        self.assert_(m.startProductionState == state_Maintenance)

    def setupWindows(self, windowsDefs, maxWindows=10):
        """
        Setup windows from time t0 to time tmaxWindows-1

        Window defintions are a list of lists of the form
             [startTimeIndex, duration, startState]
        """
        class multiWindow: pass
        multiWin = multiWindow()

        # Create the test device
        multiWin.devid = 'unittestdevice1'
        multiWin.grpid = 'unittestGroup'
        multiWin.grp = self.dmd.Groups.createOrganizer(multiWin.grpid)
        # Note: A device's default creation state is state_Production
        multiWin.dev = self.dmd.Devices.createInstance(multiWin.devid)
        multiWin.dev.setGroups(multiWin.grp.id)

        multiWin.startDate = '01/29/2006'
        startDate_time = [ 2006, 1, 31, 10, 00, 12, 0, 0, 0 ]
        multiWin.tn = range(1,maxWindows)
        multiWin.time_tn = []
        multiWin.mwIds = []
        multiWin.mwObjs = []
        for time_point in multiWin.tn:
            startDate_time[3] = time_point
            multiWin.time_tn.append( mktime(startDate_time) )

            # Create a new window
            mwid = 'testNestedwindow%d' % time_point
            multiWin.mwIds.append(mwid)
            multiWin.grp.manage_addMaintenanceWindow(mwid)

            multiWin.mwObjs.append(
                  multiWin.grp.maintenanceWindows._getOb(mwid)
            )

        index = 0
        for startTimeIndex, duration, startState in windowsDefs:
            self.assert_( index < len(multiWin.mwObjs))
            #r = FakeRequest()
            r = None
            mw = multiWin.mwObjs[index]

            startTime = multiWin.tn[startTimeIndex]
            mw.manage_editMaintenanceWindow(
                startDate=multiWin.startDate, startHours=str(startTime),
                durationHours=str(duration),
                startProductionState=startState,
                REQUEST=r)
            #self.assertEquals(r.get('message', ''), 'Saved Changes')
            index += 1

        return multiWin


    def testSingleWindow(self):
        windowDefs = [
           [0, 2, state_Pre_Production],
           [3, 2, state_Decommissioned],
        ]

        mws = self.setupWindows(windowDefs)
        dev_orig_state = mws.dev.productionState

        # Begin first window
        mws.mwObjs[0].begin(now=mws.time_tn[0])
        self.assert_(mws.dev.productionState == mws.mwObjs[0].startProductionState)
        mws.mwObjs[0].end()
        self.assert_(mws.dev.productionState == dev_orig_state)

        # Begin second window
        mws.mwObjs[1].begin(now=mws.time_tn[3])
        self.assert_(mws.dev.productionState == mws.mwObjs[1].startProductionState)
        mws.mwObjs[1].end()
        self.assert_(mws.dev.productionState == dev_orig_state)


    def testNestedWindows(self):
        """
        Test nested windows from time t0 to time t4
        """
        windowDefs = [
           [0, 4, state_Pre_Production],
           [1, 2, state_Decommissioned],
        ]
        mws = self.setupWindows(windowDefs)
        dev_orig_state = mws.dev.productionState
        mws.mwObjs[0].begin(now=mws.time_tn[0])
        self.assert_(mws.dev.productionState == mws.mwObjs[0].startProductionState)

        # Begin nested window
        mws.mwObjs[1].begin(now=mws.time_tn[1])
        self.assert_(mws.dev.productionState == min(mws.mwObjs[0].startProductionState,
                                                    mws.mwObjs[1].startProductionState))
        mws.mwObjs[1].end()
        self.assert_(mws.dev.productionState == mws.mwObjs[0].startProductionState)
        # End of nested window

        # Now end last maintenance window
        mws.mwObjs[0].end()

        self.assert_(mws.dev.productionState == dev_orig_state)


    def testOverlappingWindows(self):
        """
        Look for issues with overlapping windows
        """
        windowDefs = [
           [0, 3, state_Pre_Production],
           [1, 5, state_Decommissioned],
        ]

        mws = self.setupWindows(windowDefs)
        dev_orig_state = mws.dev.productionState
        mws.mwObjs[0].begin(now=mws.time_tn[0])
        self.assert_(mws.dev.productionState == mws.mwObjs[0].startProductionState)

        # Begin nested window
        mws.mwObjs[1].begin(now=mws.time_tn[1])
        self.assert_(mws.dev.productionState == min(mws.mwObjs[0].startProductionState,
                                                    mws.mwObjs[1].startProductionState))
        # End first window
        mws.mwObjs[0].end()
        self.assert_(mws.dev.productionState == mws.mwObjs[1].startProductionState)

        # Now end last maintenance window
        mws.mwObjs[1].end()

        self.assert_(mws.dev.productionState == dev_orig_state)


    def testSameWindowEndTime(self):
        """
        Maintenance windows are processed by zenjobs in batch so the ordering
        of when two maintenance windows that end at the same time get processed
        are different. Since maintenance windows always return to the device's
        original state this should always succeed.
        """
        windowDefs = [
           [0, 3, state_Pre_Production],
           [1, 2, state_Decommissioned],
        ]

        mws = self.setupWindows(windowDefs)
        dev_orig_state = mws.dev.productionState

        # Begin first window
        mws.mwObjs[0].begin(now=mws.time_tn[0])
        self.assert_(mws.dev.productionState == mws.mwObjs[0].startProductionState)

        # Begin second window
        mws.mwObjs[1].begin(now=mws.time_tn[1])
        self.assert_(mws.dev.productionState == mws.mwObjs[1].startProductionState)

        # Now end all maintenance windows
        mws.mwObjs[1].end()
        mws.mwObjs[0].end()

        self.assert_(mws.dev.productionState == dev_orig_state)


    def testDeleteRunningWindow(self):
        """
        Deleting a running maintenance windows should return all existing devices
        to a sane state before allowing themselves to be closed.
        """
        windowDefs = [
           [0, 3, state_Pre_Production],
           [1, 5, state_Decommissioned],
        ]

        mws = self.setupWindows(windowDefs)
        dev_orig_state = mws.dev.productionState

        # Begin first window
        mws.mwObjs[0].begin(now=mws.time_tn[0])
        self.assert_(mws.dev.productionState == mws.mwObjs[0].startProductionState)

        # Begin second window
        mws.mwObjs[1].begin(now=mws.time_tn[1])
        self.assert_(mws.dev.productionState == mws.mwObjs[1].startProductionState)

        # Now delete all maintenance windows
        #r = FakeRequest()
        r = None
        mws.grp.manage_deleteMaintenanceWindow(mws.mwIds[1], REQUEST=r)
        self.assert_(mws.dev.productionState == mws.mwObjs[0].startProductionState)

        #r = FakeRequest()
        r = None
        mws.grp.manage_deleteMaintenanceWindow(mws.mwIds[0], REQUEST=r)
        self.assert_(mws.dev.productionState == dev_orig_state)


    def ftestWindowStateChangeLoad(self):
        """
        The simple algorithm in use is O(n * m^2) for n devices and m windows,
        so we need to determine how bad "bad" really is in terms of running time.
        """
        windowDefs = [
           [0, 3, state_Pre_Production],
           [1, 5, state_Decommissioned],
        ]

        mws = self.setupWindows(windowDefs)
        print "Starting device creation"
        maxDevs = 2000
        for i in range(maxDevs):
           if i % 100 == 0:
               print i
           devid = "mwdev%d" % i
           dev = self.dmd.Devices.createInstance(devid)
           dev.setGroups(mws.grp.id)
        print "Finished device creation"

        # Test one window change
        now = time()
        mws.mwObjs[0].begin(now=mws.time_tn[0])
        finish = time()
        print "One maintenance window start for %d devices was %f seconds" % (
               maxDevs, finish - now)



def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestMaintenanceWindows))
    return suite
