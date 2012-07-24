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
import time
from random import random
from exceptions import *
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenRRD.RRDUtil import RRDUtil
from Products.ZenModel.Exceptions import *


class TestRRDUtil(BaseTestCase):

    def afterSetUp(self):
        super(TestRRDUtil, self).afterSetUp()

        # Make a valid test device
        testdev = str(self.__class__.__name__)

        self.name = testdev

        # name, path, dataStorageType, rrdCreateCommand, minmax
        self.path= os.path.join( "tests", testdev )

        self.dev = self.dmd.Devices.createInstance(testdev)

        #createcmd= self.dmd.Devices.findDevice(testdev).getPerformanceServer().getDefaultRRDCreateCommand()
        self.createcmd= 'RRA:AVERAGE:0.5:1:600\nRRA:AVERAGE:0.5:6:600\nRRA:AVERAGE:0.5:24:600\nRRA:AVERAGE:0.5:288:600\nRRA:MAX:0.5:6:600\nRRA:MAX:0.5:24:600\nRRA:MAX:0.5:288:600'

        rrd= RRDUtil( '', 60 )
        self.perfpath= rrd.performancePath( "tests" )


    def testGoodSave(self):
        """
        Sanity check to make sure that RRD stores work
        """
        rrd= RRDUtil( self.createcmd, 60 )

        # Create a new file, and add a value after creation
        path= os.path.join( self.path, "%f" % random() )
        self.assertEquals( rrd.save( path, 666.0, 'COUNTER' ), None )
        self.assertEquals( rrd.save( path, 666.0, 'COUNTER' ), None )


    def testBadDefaultCreateCmd(self):
        """
        Bad default command
        """
        rrd= RRDUtil( '', 60 )
        # If the file is already created, then it doesn't get tested
        path= os.path.join( self.path, "%f" % random() )
        self.assertRaises( Exception, rrd.save, path, 666.0, 'COUNTER' )

        path= os.path.join( self.path, "%f" % random() )
        self.assertRaises( Exception, rrd.save, path, 666.0, 'COUNTER', rrdCommand='' )

        path= os.path.join( self.path, "%f" % random() )
        self.assertEquals( rrd.save( path, 666.0, 'COUNTER', rrdCommand=self.createcmd ), None )


    def testMinmaxReversed(self):
        """
        What happens when the min/max values of the data point
        are reversed?
        """
        rrd= RRDUtil( self.createcmd, 60 )
        path= os.path.join( self.path, "%f" % random() )
        self.assertRaises( Exception, rrd.save, path, 666.0, 'COUNTER', min=100, max=1 )

    def testBadMinmax(self):
        """
        Illegal values for min, max
        """
        rrd= RRDUtil( self.createcmd, 60 )
        path= os.path.join( self.path, "%f" % random() )
        self.assertEquals( rrd.save( path, 666.0, 'COUNTER', min=-100 ), None )

        path= os.path.join( self.path, "%f" % random() )
        self.assertEquals( rrd.save( path, 666.0, 'COUNTER', min=None ), None )

        path= os.path.join( self.path, "%f" % random() )
        self.assertEquals( rrd.save( path, 666.0, 'COUNTER', min='U' ), None )

        path= os.path.join( self.path, "%f" % random() )
        self.assertEquals( rrd.save( path, 666.0, 'COUNTER', min=[] ), None )


    def testBadType(self):
        """
        Bad data type which only gets used at creation time
        """
        rrd= RRDUtil( self.createcmd, 60 )

        path= os.path.join( self.path, "%f" % random() )
        self.assertRaises( Exception, rrd.save, path, 666.0, 'BOGO' )

        path= os.path.join( self.path, "%f" % random() )
        self.assertRaises( Exception, rrd.save, path, 666.0, ':BOGO' )


    def testBadValues(self):
        """
        Bad data values
        """
        rrd= RRDUtil( self.createcmd, 60 )

        #print "Expecting: '%s'" % ".ERROR:zen.RRDUtil:rrd error not a simple integer: '666.0' tests/testsnmpdev"
        self.assertEquals( rrd.save( self.path, None, 'COUNTER' ), None )

        # A little inconsistent
        self.assertEquals( rrd.save( self.path, [], 'COUNTER' ), None )
        self.assertEqual( rrd.save(self.path, [], 'ABSOLUTE'), None )

        self.assertEquals( rrd.save( self.path, "hello world", 'COUNTER' ), None )
        self.assertEqual(  rrd.save(self.path, "hello world", 'ABSOLUTE'), None )


    def testNotWritableRRD(self):
        """
        Can't write to a file
        """
        # Verify that we're not root first...
        if os.geteuid() == 0:
            print "Can't run testNotWritableRRD check if running as root"
            return

        rrd= RRDUtil( self.createcmd, 60 )

        rrd.performancePath= lambda(x): "/"
        self.assertRaises( Exception, rrd.save, "/", 666.0, 'COUNTER' )

    def testLowLevelFuncs(self):
        """
        Verify info function succeeds.
        """
        rrd= RRDUtil( self.createcmd, 60 )
        path= os.path.join( self.path, "%f" % random() )

        # setup RRD file, add values to it
        startTime = time.time() - 10 * 60
        for i in range (0, 10):
            rrd.save( path, i * 100, 'COUNTER', useRRDDaemon=False, timestamp=int(startTime+i*60), start=startTime)

        # check info function
        import rrdtool
        filename = rrd.performancePath(path) + '.rrd'
        info = rrdtool.info(filename)

        self.assertEquals(info['ds[ds0].index'], 0L)
        # self.assertEquals(info['ds[ds0].last_ds'], '90.0')
        self.assertEquals(info['ds[ds0].max'], None)
        self.assertEquals(info['ds[ds0].min'], None)
        self.assertEquals(info['ds[ds0].minimal_heartbeat'], 180L)
        self.assertEquals(info['ds[ds0].type'], 'COUNTER')

        # test fetch
        data = rrdtool.fetch(filename, 'AVERAGE', '--start', "%d" % startTime)

        # check the middle of the fetch for 1.7/s rate
        self.failUnlessAlmostEqual(data[2][2][0], 1.7, places=1)
        self.failUnlessAlmostEqual(data[2][3][0], 1.7, places=1)
        self.failUnlessAlmostEqual(data[2][4][0], 1.7, places=1)
        self.failUnlessAlmostEqual(data[2][5][0], 1.7, places=1)
        self.failUnlessAlmostEqual(data[2][6][0], 1.7, places=1)
        self.failUnlessAlmostEqual(data[2][7][0], 1.7, places=1)

        # test fetch, with daemon pointing to bad socket file
        self.assertRaises(rrdtool.error, rrdtool.fetch, filename, 'AVERAGE', '--start', "%d" % startTime, '--daemon' '/tmp/blah')

        # test graph
        imFile = rrd.performancePath(path) + ".png"
        rrdtool.graph(imFile,
            "-w", "400",
            "-h", "100",
            "--full-size-mode",
            "DEF:ds0a=%s:ds0:AVERAGE" % filename,
            "LINE1:ds0a#0000FF:'default'",
        )

        def readPNGsize(fname):
            """
            PNG spec defines 16-byte header, followed by width and height as
            unsigned 4-byte integers.
            """
            import struct
            with open(fname, "rb") as pngfile:
                first24 = pngfile.read(24)
                sizebytes = first24[-8:]
                width,height = struct.unpack_from(">II",sizebytes)
                return width,height

        self.assertEquals(readPNGsize(imFile), (400, 100))

    def beforeTearDown(self):
        """
        Clean up after our tests
        """
        import shutil
        try:
            shutil.rmtree( self.perfpath )
        except:
            pass

        super(TestRRDUtil, self).beforeTearDown()



def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestRRDUtil))
    return suite
