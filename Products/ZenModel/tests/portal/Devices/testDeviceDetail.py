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

class Edahl04DetailTest(unittest.TestCase):
    '''check edahl04's device detail scnree'''
    dev = (makerequest.makerequest(Zope.app())).dmd.Devices.Servers.Linux._getOb('edahl04.confmon.loc').detail

    def testHostname(self):
        '''check hostname on edahl04'''
        self.assertEqual(
            self.dev().find('edahl04.confmon.loc') != -1, 1)

    def testDeviceType(self):
        '''make sure edahl04 is linux'''
        self.assertEqual(
            self.dev().find('Linux') != -1, 1)

    def testFileSystems(self):
        '''make sure edahl04 is blank'''
        self.assertEqual(
            self.dev().find('No File Systems') != -1, 1)

    def testRoutes(self):
        '''make sure edahl04 is blank'''
        self.assertEqual(
            self.dev().find('No Routes') != -1, 1)

class RouterDetailTest(unittest.TestCase):
    '''check router's device detail scnree'''
    dev = (makerequest.makerequest(Zope.app())).dmd.Devices.NetworkDevices.Router._getOb('router.confmon.loc').detail

    def testHostname(self):
        '''check hostname on router'''
        self.assertEqual(
            self.dev().find('router.confmon.loc') != -1, 1)

    def testDeviceType(self):
        '''make sure router is of type Router'''
        self.assertEqual(
            self.dev().find('Router') != -1, 1)

    def testNetworks(self):
        '''make sure router is in 10.2.1.0'''
        self.assertEqual(
            self.dev().find("'/dmd/Networks/10.2.1.0'") != -1, 1)

    def testRoutes(self):
        '''make sure router is blank'''
        self.assertEqual(
            self.dev().find('No Routes') != -1, 1)

if __name__=="__main__":
    unittest.main()
