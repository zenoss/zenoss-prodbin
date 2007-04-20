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
import time


class SystemSearchTest(unittest.TestCase):
    '''try searching through systems'''
    search = (makerequest.makerequest(Zope.app())).dmd.Systems.searchResults

    #####################################################
    #   System test methods
    #####################################################

    def testFindConfmonSystem(self):
        '''test to find the confmon system'''
        self.assertEqual(
            self.search(query="Confmon").find('"/dmd/Systems/Confmon"') != -1, 1)
    
    def testFindConfStarSystem(self):
        '''test to find conf* in systems'''
        self.assertEqual(
            self.search(query="conf*").find('"/dmd/Systems/Confmon"') != -1, 1)

    def testFindGatewaySystem(self):
        '''test to find the gateway subsystem in confmon'''
        self.assertEqual(
            self.search(query="Gateway").find('"/dmd/Systems/Confmon/subsystems/Gateway"') != -1, 1)

    def testFindGateStarSystem(self):
        '''test to find the gate* system'''
        self.assertEqual(
            self.search(query="gate*").find('"/dmd/Systems/Confmon/subsystems/Gateway"') != -1, 1)

    def testFindAbsentSystem(self):
        '''find something that doesn't exist'''
        self.assertEqual(
            self.search(query="absent").find("matched absent") != -1, 1)

class DeviceSearchTest(unittest.TestCase):
    '''try searching through devices'''
    search = (makerequest.makerequest(Zope.app())).dmd.Devices.searchResults

    #####################################################
    #   Device search methods
    #####################################################

    def testFindEdahl04Device(self):
        '''test to find edahl04'''
        self.assertEqual(
            self.search(query="edahl04").find('"/dmd/Devices/Servers/Linux/edahl04.confmon.loc"') != -1, 1)

    def testFindEdahlStarDevice(self):
        '''test to find edahl* (make sure globbing works)'''
        self.assertEqual(
            self.search(query="edahl*").find('"/dmd/Devices/Servers/Linux/edahl04.confmon.loc"') != -1, 1)

    def testFindEdahlFqdnDevice(self):
        '''test to find edal04.confmon.loc'''
        self.assertEqual(
            self.search(query="edahl04.confmon.loc").find('"/dmd/Devices/Servers/Linux/edahl04.confmon.loc"') != -1, 1)

    def testFindEdahlIpDevice(self):
        '''test to find 10.2.1.1'''
        self.assertEqual(
            self.search(query="10.2.1.1").find('"/dmd/Devices/Servers/Linux/edahl04.confmon.loc"') != -1, 1)

    def testFindRouterDevice(self):
        '''test to find router'''
        self.assertEqual(
            self.search(query="router").find('"/dmd/Devices/NetworkDevices/Router/router.confmon.loc"') != -1, 1)

    def testFindRouterStarDevice(self):
        '''test to find router*'''
        self.assertEqual(
            self.search(query="router*").find('"/dmd/Devices/NetworkDevices/Router/router.confmon.loc"') != -1, 1)

    def testFindRouterFqdnDevice(self):
        '''test to find router.confmon.loc'''
        self.assertEqual(
            self.search(query="router.confmon.loc").find('"/dmd/Devices/NetworkDevices/Router/router.confmon.loc"') != -1, 1)

    def testFindRouterIpDevice(self):
        '''test to find 10.2.1.5'''
        self.assertEqual(
            self.search(query="10.2.1.5").find('"/dmd/Devices/NetworkDevices/Router/router.confmon.loc"') != -1, 1)

    def testFindAbsentDevice(self):
        '''find something that doesn't exist'''
        self.assertEqual(
            self.search(query="absent").find("matched absent") != -1, 1)

if __name__=="__main__":
    unittest.main()
