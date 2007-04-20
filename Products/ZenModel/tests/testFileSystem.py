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
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Products.ZenModel.Exceptions import *
from Products.ZenModel.FileSystem import FileSystem

from ZenModelBaseTest import ZenModelBaseTest

class TestFileSystem(ZenModelBaseTest):


    def setUp(self):
        ZenModelBaseTest.setUp(self)
        self.dev = self.dmd.Devices.createInstance('testdev')
        tmpo = FileSystem('fs')
        self.dev.os.filesystems._setObject('fs',tmpo)
        self.fs = self.dev.os.filesystems()[0]


    def testSetManageIp(self):
        self.fs.setManageIp('1.2.3.4/24')
        self.assert_(self.fs.getManageIp() == '1.2.3.4/24')
        self.assert_(self.dev.getManageIp() == '1.2.3.4/24')
        self.dev.setManageIp('2.3.4.5/24')
        self.assert_(self.fs.getManageIp() == '2.3.4.5/24')


    def testGets(self):
        # XXX these depend upon fs.mount being set, and that is done by the
        # collector, so it's kind of hard to test here. When collector unit
        # tests are written, these should be deleted from here and added there.
        #self.assert_(self.fs.getInstDescription() == 'fs')
        #self.assert_(self.fs.name() == 'fs')
        self.assert_(self.fs.hostname() == 'testdev')
        self.assert_(self.fs.getParentDeviceName() == 'testdev')
        #self.assert_(self.fs.getParentDeviceUrl() == 'zport/dmd/Devices/devices/testdev')
        self.assert_(self.fs.getParentDeviceUrl() == 'http://nohost/zport/dmd/Devices/devices/testdev')

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestFileSystem))
    return suite

if __name__=="__main__":
    framework()
