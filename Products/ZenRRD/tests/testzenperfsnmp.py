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
from Products.ZenRRD.zenperfsnmp import OidData, zenperfsnmp
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


class Testzenperfsnmp(BaseTestCase):

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

        self.oidData= OidData()
        # name, path, dataStorageType, rrdCreateCommand, minmax
        self.path= os.path.join( "tests", testdev )
        self.oidData.update( testdev, self.path, "COUNTER", None, 
                             (0, 100) )

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

        self.zpf = zenperfsnmp( noopts=1 )
        # default RRD create command, cycle interval
        self.zpf.rrd= RRDUtil( defrrdcmd, 60 )

        # Fake out some options for sending alerts
        self.zpf.options = FakeOptions()
        self.zpf.options.monitor = testdev

        # Save the following info for our tearDown() script
        self.perfpath= self.zpf.rrd.performancePath( "tests" )
        self.zpf.rrd.performancePath= lambda(x): os.path.join( self.perfpath, x )



    def testEthernetPerfGather(self):
        """
        Gather some localhost Ethernet stats
        """
        # Not complete
        return

        snmpProps = {
            'id':self.name,
            'manageIp':'127.0.0.1',
            'zMaxOIDPerRequest':10,
            'zSnmpMonitorIgnore':False,
            'zSnmpCommunity':'public',
            'zSnmpPort':161,
            'zSnmpVer':['1'],
        }

        device = FakeDevice( self.name, **snmpProps )

        from Products.ZenHub.services.PerformanceConfig import SnmpConnInfo
        self.conn = SnmpConnInfo( device )

        configs = FakeConfigs( self.name, [], self.conn )

        self.zpf.updateDeviceConfig( configs ) 

        
    def rrdsave_setup(self, oid, data ):
        class FakeProxy: pass
        proxy = FakeProxy()
        proxy.oidMap = {}
        proxy.oidMap[ oid ] = data
        self.zpf.proxies[ self.name ]= proxy


    def testGoodRRDSave(self):
        """
        Sanity check to make sure that RRD stores work
        """
        oid = "1.3.6.1.666.1.0"

        data = self.oidData
        self.rrdsave_setup( oid, data )
        self.zpf.storeRRD( self.name, oid, 666.0 )


    def testRRDminmaxReversed(self):
        """
        What happens when the min/max values of the data point
        are reversed?
        """
        oid = "1.3.6.1.666.2.0"

        data= self.oidData
        (min,max) = data.minmax
        data.minmax = (max,min)
        self.rrdsave_setup( oid, data )
        self.zpf.storeRRD( self.name, oid, 666.0 )


    def testBadDevice(self):
        """
        Should never happen
        """
        oid = "1.3.6.1.666.1.0"
        self.assertRaises( KeyError, self.zpf.storeRRD, "nessie", oid, 666.0 )


    def testUnableToWrite(self):
        """
        Can't write to disk
        """
        # Verify that we're not root first...
        if os.geteuid() == 0:
            print "Can't run testUnableToWrite check if running as root"
            return

        oid= "1.3.6.1.666.1.0"

        data = self.oidData
        self.rrdsave_setup( oid, data )
        old = self.zpf.rrd.performancePath

        # This will try to create a /.rrd file, which should fail
        self.zpf.rrd.performancePath= lambda(x): "/"

        # Fake out sendEvent
        evts = []
        def append(evt):
            if evt['severity'] != 0:
                evts.append(evt)
        self.zpf.sendEvent = append

        self.zpf.storeRRD( self.name, oid, 666.0 )
        self.zpf.rrd.performancePath = old

        self.assertNotEquals( len(evts), 0 )


    def tearDown(self):
        """
        Clean up after our tests
        """
        import shutil
        try:
            shutil.rmtree( self.perfpath )
        except:
            pass

        BaseTestCase.tearDown(self)



def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(Testzenperfsnmp))
    return suite

