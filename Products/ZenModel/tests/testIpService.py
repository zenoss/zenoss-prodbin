#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################
import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import pdb
import unittest

import Globals
import transaction

from Products.ZenModel.Exceptions import *
from Products.ZenUtils.ZeoConn import ZeoConn
from Products.ZenModel.IpService import IpService

zeoconn = ZeoConn()

class TestIpService(unittest.TestCase):

    def setUp(self):
        self.dmd = zeoconn.dmd
        self.dev = self.dmd.Devices.createInstance("testdev")
        tmpo = IpService('ipsvc')
        self.dev.os.ipservices._setObject('ipsvc',tmpo)
        self.ipsvc = self.dev.os.ipservices()[0]


    def tearDown(self):
        transaction.abort()
        self.dmd = None
    

    def testSetIpService(self):
        self.ipsvc.port = 121 #for now, so that setIpService is actually useful
        self.ipsvc.protocol = 'tcp' #ditto
        self.ipsvc.setServiceClass({'protocol':'tcp','port':121})
        self.assert_(self.ipsvc.getProtocol() == 'tcp')
        self.assert_(self.ipsvc.getPort() == 121)
        self.assert_(self.ipsvc.getServiceClass()['protocol'] == 'tcp')
        self.assert_(self.ipsvc.getServiceClass()['port'] == 121)
        self.assert_(self.ipsvc.getKeyword() == self.ipsvc.serviceclass().name)
        self.assert_(self.ipsvc.getDescription() == self.ipsvc.serviceclass().description)
        self.assert_(self.ipsvc.primarySortKey() == 'tcp-00121')
        self.assert_(self.ipsvc.getInstDescription() == 'tcp-121 ips:')
        self.assert_(self.ipsvc.hostname() == 'testdev')


    def testSetManageIp(self):
        self.ipsvc.setManageIp('1.2.3.4/24')
        self.assert_(self.ipsvc.getManageIp() == '1.2.3.4/24')
        self.assert_(self.dev.getManageIp() == '1.2.3.4/24')
        self.dev.setManageIp('2.3.4.5/24')
        self.assert_(self.ipsvc.getManageIp() == '2.3.4.5/24')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestIpService))
    return suite

if __name__=="__main__":
    framework()
