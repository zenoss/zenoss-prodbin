##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import time
import unittest
import json
from datetime import datetime

import Globals

from zope.interface import Interface, implements

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.Five import zcml

import Products.ZenCallHome
from Products.ZenCallHome import ICallHomeCollector
from Products.ZenCallHome.callhome import CallHomeCollector, CallHomeData, EXTERNAL_ERROR_KEY
from Products.ZenCallHome.transport import CallHome, CallHomeData as PersistentCallHomeData
from Products.ZenCallHome.transport.crypt import decrypt

DATETIME_ISOFORMAT='%Y-%m-%dT%H:%M:%S.%f'

TEST_DATA="""
<configure xmlns="http://namespaces.zope.org/zope"
           xmlns:five="http://namespaces.zope.org/five">
      <utility component="Products.ZenCallHome.tests.testCallHomeGeneration.TestCallHomeData"
               provides="Products.ZenCallHome.tests.testCallHomeGeneration.ITestCallHomeData"
               name="testdata"/>
      </configure>
"""

FAILING_TEST_DATA="""
<configure xmlns="http://namespaces.zope.org/zope"
           xmlns:five="http://namespaces.zope.org/five">
      <utility component="Products.ZenCallHome.tests.testCallHomeGeneration.FailingTestCallHomeData"
               provides="Products.ZenCallHome.tests.testCallHomeGeneration.ITestCallHomeData"
               name="failingtestdata"/>
      </configure>
"""

SIMPLE_SUCCESS_COLLECTOR="""
<configure xmlns="http://namespaces.zope.org/zope"
           xmlns:five="http://namespaces.zope.org/five">
      <utility component="Products.ZenCallHome.tests.testCallHomeGeneration.SimpleSuccessCollector"
               provides="Products.ZenCallHome.ICallHomeCollector"
               name="simplesuccess"/>
      </configure>
"""

SIMPLE_SUCCESS_KEY="simplesuccess"

FAST_FAIL_COLLECTOR="""
<configure xmlns="http://namespaces.zope.org/zope"
           xmlns:five="http://namespaces.zope.org/five">
     <utility component="Products.ZenCallHome.tests.testCallHomeGeneration.FastFailCollector"
                     provides="Products.ZenCallHome.ICallHomeCollector"
                     name="fastfail"/>
     </configure>
"""

FAST_FAIL_KEY="fastfail"

FAST_FAIL_ERROR_MESSAGE="Fast failed at collector level"
FAILING_DATA_ERROR_MESSAGE="Failed individual test data"


class ITestCallHomeData(Interface):
    """
    """
    def callHomeData(self):
        """
        """

class TestCallHomeData(object):
    implements(ITestCallHomeData)
    def callHomeData(self):
        yield "test", "test"

class FailingTestDataException(Exception):
    pass

class FailingTestCallHomeData(object):
    implements(ITestCallHomeData)
    def callHomeData(self):
        raise FailingTestDataException(FAILING_DATA_ERROR_MESSAGE)

class SimpleSuccessCollector(CallHomeCollector):
    """
    Default success collector as a control variable
    """
    implements(ICallHomeCollector)
    def __init__(self):
        super(SimpleSuccessCollector,self).__init__(ITestCallHomeData)
        self._key=SIMPLE_SUCCESS_KEY

class FastFailTestException(Exception):
    pass

class FastFailCollector(CallHomeCollector):
    """
    Default success collector as a control variable
    """
    implements(ICallHomeCollector)
    def __init__(self):
        super(FastFailCollector,self).__init__(ITestCallHomeData)
        self._key=FAST_FAIL_KEY

    def generateData(self):
        raise FastFailTestException(FAST_FAIL_ERROR_MESSAGE)

class testCallHomeGeneration(BaseTestCase):

    def afterSetUp(self):
        super(testCallHomeGeneration, self).afterSetUp()
        zcml.load_config('meta.zcml', Products.ZenCallHome)
        zcml.load_config('configure.zcml', Products.ZenCallHome)

    def beforeTearDown(self):
        super(testCallHomeGeneration, self).beforeTearDown()

    def checkForExistingCallHomeData(self):
        try:
            self.dmd.callHome 
            self.fail("New zodb instance should not have callhome data")
        except AttributeError:
            pass

    def testCallHomeCollectorFailure(self):
        # check current version of report (should be empty)
        self.checkForExistingCallHomeData()

        # register bad acting callhome collector via zcml (or directly)
        zcml.load_string( TEST_DATA )
        zcml.load_string( SIMPLE_SUCCESS_COLLECTOR )
        zcml.load_string( FAST_FAIL_COLLECTOR )

        # call callhome scripting
        chd = CallHomeData(self.dmd, True)
        data = chd.getData()

        # make sure report has data from default collectors and 
        # successful collector, but not the failing collector
        self.assertTrue( "Zenoss Env Data" in data )
        self.assertTrue( SIMPLE_SUCCESS_KEY in data )
        self.assertTrue( FAST_FAIL_KEY not in data )
        self.assertTrue( EXTERNAL_ERROR_KEY in data )
        self.assertEquals( FAST_FAIL_ERROR_MESSAGE, data[EXTERNAL_ERROR_KEY][0]['exception'] )

    def testConstituentDataFailure(self):
        # check current version of report (should be empty?)
        self.checkForExistingCallHomeData()
        
        # register bad acting callhome collector via zcml (or directly)
        zcml.load_string( FAILING_TEST_DATA )
        zcml.load_string( TEST_DATA )
        zcml.load_string( SIMPLE_SUCCESS_COLLECTOR )

        # call callhome scripting
        chd = CallHomeData(self.dmd, True)
        data = chd.getData()

        # make sure report has basic values even though part failed.
        # specifically make sure that simple success section is present
        # and that the successful data entry is there and the failed
        # entry is not
        self.assertTrue( "Zenoss Env Data" in data )
        self.assertTrue( SIMPLE_SUCCESS_KEY in data )
        successData = data[SIMPLE_SUCCESS_KEY]
        self.assertTrue( "test" in successData )
        self.assertTrue( EXTERNAL_ERROR_KEY in data )
        self.assertEquals( FAILING_DATA_ERROR_MESSAGE, data[EXTERNAL_ERROR_KEY][0]['exception'] )

    def testPayloadGeneration(self):
        # check current version of report (should be empty)
        self.checkForExistingCallHomeData()
        
        # call callhome scripting
        beforeReportGeneration = datetime.utcnow()
        chd = CallHomeData(self.dmd, True)
        data = chd.getData()
        afterReportGeneration = datetime.utcnow()

        time.sleep(1)

        # Unfortunately the cycler code can't be disentagled
        # from itself for testability so we have to mimic it
        # for this test case.
        # What happens is that CallHomeCycler 
        # kicks off the callhome script (callhome.py)
        # and takes the process output as a string
        # and stores it in the callhome object
        # in zodb (dmd.callHome). In callhome.py you can
        # see that the Main class spits out the 
        # json.dumps of the output of CallHomeData.getData.
        self.dmd.callHome = PersistentCallHomeData()
        self.dmd.callHome.metrics = json.dumps( data )

        # create the actual payload that will be sent
        beforePayloadGeneration = datetime.utcnow()
        payloadGenerator = CallHome( self.dmd )
        payload = payloadGenerator.get_payload(False)
        afterPayloadGeneration = datetime.utcnow()

        # decrypt payload and reconstitute object
        payloadObj = json.loads( payload )
       
        # make sure payload has the required fields
        self.assertTrue( 'product' in payloadObj )
        self.assertTrue( 'uuid' in payloadObj )
        self.assertTrue( 'symkey' in payloadObj )
        self.assertTrue( 'metrics' in payloadObj )
       
        # reconstitute metrics obj & make sure send date is present
        # and has a valid time
        metricsObj = json.loads( payloadObj['metrics'] )
        self.assertTrue( 'Send Date' in metricsObj )
        sendDateDT = datetime.strptime( metricsObj['Send Date'], DATETIME_ISOFORMAT )
        reportDateDT = datetime.strptime( metricsObj['Report Date'], DATETIME_ISOFORMAT )
        self.assertTrue( reportDateDT < sendDateDT )
        self.assertTrue( beforeReportGeneration <= reportDateDT <= afterReportGeneration )
        self.assertTrue( beforePayloadGeneration <= sendDateDT <= afterPayloadGeneration )
        

    #
    # UNFORTUNATELY CANNOT EASILY UNIT TEST TIMEOUTS BECAUSE
    # OF THE CROSS-PROCESS STEPS
    #
    #def testTimeOutCallHomeCollector(self):
        # check current version of report (should be empty?)
        # register bad acting callhome collector via zcml (or directly)
        # call callhome scripting
        # make sure report has basic values even though part failed 


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testCallHomeGeneration))
    return suite

if __name__=="__main__":
    framework()
