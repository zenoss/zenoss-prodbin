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
from Products.ZenModel.FileSystem import FileSystem

zeoconn = ZeoConn()

class TestFileSystem(unittest.TestCase):

    def setUp(self):
        self.dmd = zeoconn.dmd
        self.dev = self.dmd.Devices.createInstance('testdev')
        tmpo = FileSystem('fs')
        self.dev.os.filesystems._setObject('fs',tmpo)
        self.fs = self.dev.os.filesystems()[0]


    def tearDown(self):
        transaction.abort()
        self.dmd = None


    def testSetManageIp(self):
        self.fs.setManageIp('1.2.3.4/24')
        self.assert_(self.fs.getManageIp() == '1.2.3.4/24')
        self.assert_(self.dev.getManageIp() == '1.2.3.4/24')
        self.dev.setManageIp('2.3.4.5/24')
        self.assert_(self.fs.getManageIp() == '2.3.4.5/24')


    def testGets(self):
        self.assert_(self.fs.getInstDescription() == 'fs')
        self.assert_(self.fs.name() == 'fs')
        self.assert_(self.fs.hostname() == 'testdev')
        self.assert_(self.fs.getParentDeviceName() == 'testdev')
        self.assert_(self.fs.getParentDeviceUrl() == 'zport/dmd/Devices/devices/testdev')

def main():

       unittest.TextTestRunner().run(test_suite())

if __name__=="__main__":
       unittest.main()
