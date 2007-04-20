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

__version__ = "$Revision: 1.2 $"[11:-2]

import unittest
import Zope
from Testing import makerequest

class NetworksListTest(unittest.TestCase):
    '''test the networks directory listing'''
    locs = (makerequest.makerequest(Zope.app())).dmd.Networks.index_html

    def testHasTenDot(self):
        '''make sure there is a 10.2.1.0 network'''
        self.assertEqual(
            self.locs().find('"/dmd/Networks/10.2.1.0"') != -1, 1)

class TenDotStatusTest(unittest.TestCase):
    '''test the status of the 10.2.1.0 network'''
    ten = (makerequest.makerequest(Zope.app())).dmd.Networks._getOb('10.2.1.0').view

    def testHasNoSubnets(self):
        '''make sure the 10.2.1.0 network doesn't have subnets'''
        self.assertEqual(
            self.ten().find('No Subnetworks') != -1, 1)

    def testHasMask(self):
        '''make sure the 10.2.1.0 has a /24 mask'''
        self.assertEqual(
            self.ten().find('255.255.255.0') != -1, 1)

    def testHasAddress(self):
        '''make sure it knows its address'''
        self.assertEqual(
            self.ten().find('10.2.1.0') != -1, 1)

class TenDotAddressTest(unittest.TestCase):
    '''test the network addresses screen'''
    addrs = (makerequest.makerequest(Zope.app())).dmd.Networks._getOb('10.2.1.0').addresses

    def testHasEdahl04Address(self):
        '''make sure edahl04 is in here as an address'''
        self.assertEqual(
            self.addrs().find('10.2.1.1') != -1, 1)

    def testHasEdahl04(self):
        '''make sure edahl04 is in here by name'''
        self.assertEqual(
            self.addrs().find('"/dmd/Devices/Servers/Linux/edahl04.confmon.loc"') != -1, 1)

    def testHasRouter(self):
        '''make sure router is in here as an address'''
        self.assertEqual(
            self.addrs().find('10.2.1.5') != -1, 1)

    def testHasRouter(self):
        '''make sure router is in here by name'''
        self.assertEqual(
            self.addrs().find('"/dmd/Devices/NetworkDevices/Router/router.confmon.loc"') != -1, 1)

class TenDotHistoryTest(unittest.TestCase):
    '''test the network history screen'''
    hist = (makerequest.makerequest(Zope.app())).dmd.Networks._getOb('10.2.1.0').viewHistory
    
    def testInitialLoad(self):
        '''make sure this was loaded by loader.py'''
        self.assertEqual(
            self.hist().find('Initial load') != -1, 1)

class TenDotTopTest(unittest.TestCase):
    '''test the nav bar of the 10.2.1.0 network'''
    top = (makerequest.makerequest(Zope.app())).dmd.Networks._getOb('10.2.1.0').top

    def testHasStatus(self):
        '''make sure the navbar has Status'''
        self.assertEqual(
            self.top().find('href="view"') != -1, 1)

    def testHasAddresses(self):
        '''make sure the navbar has addresses'''
        self.assertEqual(
            self.top().find('href="addresses"') != -1, 1)

    def testHasChanges(self):
        '''make sure the navbar has changes'''
        self.assertEqual(
            self.top().find('href="viewHistory"') != -1, 1)

if __name__=="__main__":
    unittest.main()
