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
from Products.ZenModel.IpInterface import IpInterface
from Products.ZenModel.IpRouteEntry import IpRouteEntry

zeoconn = ZeoConn()

class TestIpRouteEntry(unittest.TestCase):

    def setUp(self):
        self.dmd = zeoconn.dmd
        self.dev = self.dmd.Devices.createInstance('testdev')
        tmpo = IpInterface('test')
        self.dev.os.interfaces._setObject('test',tmpo)
        self.iface = self.dev.os.interfaces()[0]
        self.iface.setIpAddresses('1.2.3.4/24')
        tmpo = IpRouteEntry('rEntry')
        self.iface.routes._setObject('rEntry',tmpo)
        self.rEntry = self.iface.routes()[0]


    def tearDown(self):
        transaction.abort()
        self.dmd = None
    

    def testSetManageIp(self):
        self.rEntry.setManageIp('1.2.3.4/24')
        self.assert_(self.rEntry.getManageIp() == '1.2.3.4/24')
        self.assert_(self.iface.getManageIp() == '1.2.3.4/24')
        self.assert_(self.dev.getManageIp() == '1.2.3.4/24')

def main():

       unittest.TextTestRunner().run(test_suite())

if __name__=="__main__":
       unittest.main()
