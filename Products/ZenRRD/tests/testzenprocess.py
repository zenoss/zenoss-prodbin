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

import os
import os.path
import logging
from exceptions import *
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenRRD.zenprocess import zenprocess
from Products.ZenRRD.RRDUtil import RRDUtil
from Products.ZenModel.Exceptions import *


class FakeDevice(object):
    def __init__( self, name, **kwargs ):
        self.id= name
        for propertyName, value in kwargs.items():
            setattr(self, propertyName, value )

class FakeConfigs(object):
    def __init__( self, device, oids, connInfo, thresholds=None ):
        self.device= device
        self.oids= oids
        self.connInfo= connInfo
        self.thresholds= thresholds
        if thresholds is None:
            self.thresholds= []

class FakeOptions: pass


class Testzenprocess(BaseTestCase):

    def setUp(self):
        BaseTestCase.setUp(self)

        # Trap n toss all output to make the test prettier
        # Otherwise it will drive you insane, yelling
        # "SHUT UP! SHUT UP!" to your monitor.
        # Since no good will come of that...
        logging.disable(logging.INFO)
        logging.disable(logging.WARN)
        logging.disable(logging.ERROR)
        logging.disable(logging.CRITICAL)

        # Note: the docs (http://docs.python.org/library/logging.html#logging-levels)
        #       imply that we can override the above behaviour by passing
        #       a handler object to logging.getLogger().addHandler(handler),
        #       but that doesn't seem to work.

        # Make a valid test device
        testdev = str(self.__class__.__name__)
        self.name = testdev
        self.pidname = "testpid"
        self.statname = "teststat"

        # name, path, dataStorageType, rrdCreateCommand, minmax
        self.path= os.path.join( "tests", testdev )

        self.dev = self.dmd.Devices.createInstance(testdev)
        self.zem = self.dmd.ZenEventManager
        

        # We're not connected to zenhub so the following
        # always will be None
        perfServer = self.dev.getPerformanceServer()
        if perfServer:
            defrrdcmd= perfServer.getDefaultRRDCreateCommand()
        else:
            # We will always use this :(
            defrrdcmd= 'RRA:AVERAGE:0.5:1:600\nRRA:AVERAGE:0.5:6:600\nRRA:AVERAGE:0.5:24:600\nRRA:AVERAGE:0.5:288:600\nRRA:MAX:0.5:6:600\nRRA:MAX:0.5:24:600\nRRA:MAX:0.5:288:600'

        self.zproc = zenprocess( noopts=1 )
        # default RRD create command, cycle interval
        self.zproc.rrd= RRDUtil( defrrdcmd, 60 )

        # Fake out some options for sending alerts
        self.zproc.options = FakeOptions()
        self.zproc.options.monitor = testdev

        # Save the following info for our tearDown() script
        self.perfpath= self.zproc.rrd.performancePath( "tests" )
        self.zproc.rrd.performancePath= lambda(x): os.path.join( self.perfpath, x )



    def testGoodRRDSave(self):
        """
        Sanity check to make sure that RRD stores work
        """
        self.zproc.save( self.name, self.pidname, self.statname, 666.0, 'ABSOLUTE')


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
        if os.geteiud() == 0:
            print "Can't run testUnableToWrite check if running as root"
            return

        old = self.zproc.rrd.performancePath

        # This will try to create a /.rrd file, which should fail
        self.zproc.rrd.performancePath= lambda(x): "/"

        # Fake it out as we aren't really connected to zenhub
        self.zproc.sendEvent = self.zem.sendEvent

        self.zproc.save( self.name, self.pidname, self.statname, 666.0, 'ABSOLUTE')
        self.zproc.rrd.performancePath = old

        # Now check for our event...
        evid= self.zproc.last_evid
        self.assertNotEquals( evid, None )
        event = self.zem.getEventDetail(evid)

        #self.showevent( event )
        self.assertEquals( event.device, self.name )
        
        self.assertEquals( event.summary, "Unable to save data for process-monitor RRD Devices/Testzenprocess/os/processes/testpid/teststat" )


    def tearDown(self):
        """
        Clean up after our tests
        """
        import shutil
        try:
            #shutil.rmtree( self.perfpath )
            pass
        except:
            pass

        BaseTestCase.tearDown(self)



def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(Testzenprocess))
    return suite

