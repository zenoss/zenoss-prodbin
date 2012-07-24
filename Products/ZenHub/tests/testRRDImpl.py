##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os
import os.path
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenHub.services.RRDImpl import RRDImpl
from Products.ZenRRD.RRDUtil import RRDUtil


class TestRRDImpl(BaseTestCase):

    def createFakeDevice( self, name ):
        """
        Create a fake device with a datapoint
        """
        from Products.ZenModel.Device import manage_createDevice
        self.dev = manage_createDevice(self.dmd,
                                deviceName=name,
                                devicePath='/Test')

        from Products.ZenModel.RRDTemplate import manage_addRRDTemplate
        manage_addRRDTemplate(self.dmd.Devices.Test.rrdTemplates, 'Device')
        t = self.dmd.Devices.Test.rrdTemplates.Device
        ds = t.manage_addRRDDataSource('ds', 'BasicDataSource.COMMAND')
        dp = ds.manage_addRRDDataPoint('dp')
        thresh = t.manage_addRRDThreshold('limit', 'MinMaxThreshold')
        thresh.maxval = "100"
        thresh.dsnames = ('ds_dp',)


    def afterSetUp(self):
        super(TestRRDImpl, self).afterSetUp()

        # Make a valid test device
        testdev = str(self.__class__.__name__)
        self.name = testdev
        self.createFakeDevice( testdev )

        self.zem = self.dmd.ZenEventManager

        # We're not connected to zenhub so the following
        # always will be None
        perfServer = self.dev.getPerformanceServer()
        if perfServer:
            self.defrrdcmd= perfServer.getDefaultRRDCreateCommand()
        else:
            # We will always use this :(
            self.defrrdcmd= 'RRA:AVERAGE:0.5:1:600\nRRA:AVERAGE:0.5:6:600\nRRA:AVERAGE:0.5:24:600\nRRA:AVERAGE:0.5:288:600\nRRA:MAX:0.5:6:600\nRRA:MAX:0.5:24:600\nRRA:MAX:0.5:288:600'

        # default RRD create command, cycle interval
        rrd= RRDUtil( self.defrrdcmd, 60 )

        # Save the following info for our tearDown() script
        self.perfpath= rrd.performancePath( "tests" )
        self.dev.rrdPath= lambda: "tests"


    def testGoodRRDSave(self):
        """
        Sanity check to make sure that RRD stores work
        """
        rimpl = RRDImpl(self.dmd)
        rimpl.writeRRD(self.dev.id, '', '', 'ds_dp', 66)


    def testThreshold(self):
        """
        Exceed a threshhold
        """
        rimpl = RRDImpl(self.dmd)
        evts = []
        def append(evt):
            if evt['severity'] != 0:
                evts.append(evt)
        oldSendEvent = rimpl.zem.sendEvent
        rimpl.zem.sendEvent = append

        try:
            rimpl.writeRRD(self.dev.id, '', '', 'ds_dp', 99)
            self.assert_(len(evts) == 0)

            rimpl.writeRRD(self.dev.id, '', '', 'ds_dp', 101)
            self.assert_(len(evts) != 0)
        finally:
            rimpl.zem.sendEvent = oldSendEvent



    def showevent(self, event):
        """
        For debugging purposes, display an event
        """
        for field in event._fields:
            print "\t%s= %s" % (field, getattr(event, field) )


    def testUnableToWrite(self):
        """
        Can't write to disk
        """
        # Verify that we're not root first... 
        if os.geteuid() == 0:
            print "Can't run testUnableToWrite check if running as root"
            return

        # First override sendEvent
        rimpl = RRDImpl(self.dmd)
        evts = []
        def append(evt):
            if evt['severity'] != 0:
                evts.append(evt)
        rimpl.zem.sendEvent = append

        # Store a value.  As RRDImpl caches references to
        # previously stored writes, this allows us to go
        # behind the scenes to diddle with the underlying
        # RRDUtil object (stored in rimpl.rrd)
        self.assertEquals( rimpl.writeRRD(self.dev.id, '', '', 'ds_dp', 66), 66 )
        self.assertEquals(len(evts), 0)

        # This will try to create a /.rrd file, which should fail
        for key in rimpl.rrd.keys():
            rimpl.rrd[key].performancePath= lambda(x): "/"

        self.assertEquals( rimpl.writeRRD(self.dev.id, '', '', 'ds_dp', 66), None )

        # Now check for our event...
        self.assertNotEquals(len(evts), 0)


    def beforeTearDown(self):
        """
        Clean up after our tests
        """
        import shutil
        try:
            shutil.rmtree( self.perfpath )
        except:
            pass

        super(TestRRDImpl, self).beforeTearDown()



def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestRRDImpl))
    return suite
