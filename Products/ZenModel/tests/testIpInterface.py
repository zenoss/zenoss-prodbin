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

zeoconn = ZeoConn()

class TestIpInterface(unittest.TestCase):

    def setUp(self):
        from Products.ZenModel.IpInterface import IpInterface
        self.dmd = zeoconn.dmd
        tmpo = IpInterface('test')
        self.dev = self.dmd.Devices.createInstance('testdev')
        self.dev.os.interfaces._setObject('test',tmpo)
        self.iface = self.dev.getDeviceComponents()[0]
        self.iface.interfaceName = 'test'
        self.iface.macaddress = '00:00:00:00:00:00'


    def tearDown(self):
        transaction.abort()
        self.dmd = None


    def testAddIpAddress(self):
        self.iface.addIpAddress('1.2.3.4')
        self.assert_('1.2.3.4/24' in self.iface.getIpAddresses())
        self.assert_(self.iface.getIpAddress() == '1.2.3.4/24')#2 birds...
        self.assert_(self.iface.getIp() == '1.2.3.4')#and 3
        
        self.iface.addIpAddress('2.3.4.5')
        self.assert_('2.3.4.5/24' in self.iface.getIpAddresses())
        self.assert_('1.2.3.4/24' in self.iface.getIpAddresses())
        self.assert_(self.iface.getIpAddress() == '1.2.3.4/24')#it's primary
        self.assert_(self.iface.getIp() == '1.2.3.4')#ditto
        
        self.iface.removeIpAddress('1.2.3.4')
        self.assert_('1.2.3.4/24' not in self.iface.getIpAddresses())
        self.assert_('2.3.4.5/24' in self.iface.getIpAddresses())
        self.assert_(self.iface.getIpAddress() == '2.3.4.5/24')#primary changed
        self.assert_(self.iface.getIp() == '2.3.4.5')#ditto


    def testGetInterfaceMacaddress(self):
        self.assert_(self.iface.getInterfaceMacaddress() == '00:00:00:00:00:00')
        

    def testViewName(self):
        self.assert_(self.iface.viewName() == 'test')
        self.assert_(self.iface.getInterfaceName() == 'test')


    def testGetIpAddressObjs(self):
        from Products.ZenModel.IpAddress import IpAddress
        self.iface.removeIpAddress('127.0.0.1')#start empty
        add = IpAddress('1.2.3.4')
        self.iface.ipaddresses._setObject('1.2.3.4',add)
        self.assert_(self.iface.getIpAddressObj().getIp() == add.getIp())
        self.assert_(add in self.iface.getIpAddressObjs())
        add2 = IpAddress('2.3.4.5')
        self.iface.ipaddresses._setObject('2.3.4.5',add2)
        self.assert_(add2 in self.iface.getIpAddressObjs())
        self.assert_(self.iface.getIpAddressObj().getIp() == add.getIp())
        self.iface.removeIpAddress('1.2.3.4')
        self.assert_(add2 in self.iface.getIpAddressObjs())
        self.assert_(add not in self.iface.getIpAddressObjs())
        self.assert_(self.iface.getIpAddressObj().getIp() == add2.getIp())


    def testGetNetworkName(self):
        self.iface.addIpAddress('1.2.3.4')
        self.assert_(self.iface.getNetworkName() == '1.2.3.0/24')



def main():

       unittest.TextTestRunner().run(test_suite())

if __name__=="__main__":
       unittest.main()
