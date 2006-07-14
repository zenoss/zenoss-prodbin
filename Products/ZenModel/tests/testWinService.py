#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import pdb
import unittest

import Globals
import transaction

from Products.ZenModel.Exceptions import *
from Products.ZenUtils.ZeoConn import ZeoConn
from Products.ZenModel.WinService import WinService

zeoconn = ZeoConn()

class TestWinService(unittest.TestCase):

    def setUp(self):
        self.dmd = zeoconn.dmd
        self.dev = self.dmd.Devices.createInstance("testdev")
        tmpo = WinService('wsvc')
        self.dev.os.winservices._setObject('wsvc',tmpo)
        self.wsvc = self.dev.os.winservices()[0]
        self.wsvc.dmd = self.dmd #temporary fix -> setServiceClass


    def tearDown(self):
        transaction.abort()
        self.dmd = None


    def testSetServiceClass(self):
        self.wsvc.setServiceClass({'name':'ALG','description':'testsvc'})
        self.assert_(self.wsvc.name() == 'ALG')
        self.assert_(self.wsvc.caption() == 'Application Layer Gateway Service')
        self.assert_(self.wsvc.getInstDescription() == \
                     "'%s' StartMode: StartName:" % (self.wsvc.caption())\
                    )
    
    
    def testSetManageIp(self):
        self.wsvc.setManageIp('1.2.3.4/24')
        self.assert_(self.wsvc.getManageIp() == '1.2.3.4/24')
        self.assert_(self.dev.getManageIp() == '1.2.3.4/24')
        self.dev.setManageIp('2.3.4.5/24')
        self.assert_(self.wsvc.getManageIp() == '2.3.4.5/24')


    def testGets(self):
        self.assert_(self.wsvc.hostname() == 'testdev')
        self.assert_(self.wsvc.getParentDeviceName() == 'testdev')
        self.assert_(self.wsvc.getParentDeviceUrl() =='/zport/dmd/Devices/devices/testdev')
        

def main():

       unittest.TextTestRunner().run(test_suite())

if __name__=="__main__":
       unittest.main()
