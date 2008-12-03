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
from random import random
from exceptions import *
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenRRD.RRDUtil import RRDUtil
from Products.ZenModel.Exceptions import *


class TestRRDUtil(BaseTestCase):

    def setUp(self):
        BaseTestCase.setUp(self)

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
        self.assertRaises( TypeError, rrd.save, self.path, [], 'ABSOLUTE' )

        self.assertEquals( rrd.save( self.path, "hello world", 'COUNTER' ), None )
        self.assertRaises( ValueError, rrd.save, self.path, "hello world", 'ABSOLUTE' )


    def testNotWritableRRD(self):
        """
        Can't write to a file
        """
        rrd= RRDUtil( self.createcmd, 60 )

        # Should probably verify that we're not root first...
        rrd.performancePath= lambda(x): "/"
        self.assertRaises( Exception, rrd.save, "/", 666.0, 'COUNTER' )

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
    suite.addTest(makeSuite(TestRRDUtil))
    return suite

