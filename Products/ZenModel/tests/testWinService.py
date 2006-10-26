#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################
import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Products.ZenModel.Exceptions import *
from Products.ZenModel.WinService import WinService

from ZenModelBaseTest import ZenModelBaseTest


class TestWinService(ZenModelBaseTest):

    def setUp(self):
        ZenModelBaseTest.setUp(self)

        self.dev = self.dmd.Devices.createInstance("testdev")
        tmpo = WinService('wsvc')
        self.dev.os.winservices._setObject('wsvc',tmpo)
        self.wsvc = self.dev.os.winservices()[0]
        self.wsvc.dmd = self.dmd #temporary fix -> setServiceClass


    def testSetServiceClass(self):
        self.wsvc.setServiceClass({'name':'ALG','description':'testsvc'})
        self.assert_(self.wsvc.name() == 'ALG')
        import pdb;pdb.set_trace()
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
        import pdb;pdb.set_trace()
        self.assert_(self.wsvc.getParentDeviceUrl() =='/zport/dmd/Devices/devices/testdev')

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestWinService))
    return suite

if __name__=="__main__":
    framework()
