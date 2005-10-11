#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__version__ = "$Revision: 1.2 $"[11:-2]

import unittest
import Zope
from Testing import makerequest

class DeviceTopListTest(unittest.TestCase):
    '''test the top-level listing of the devices'''
    devices = (makerequest.makerequest(Zope.app())).dmd.Devices.index_html

    def testSeeNetworkDevices(self):
        '''test to see if the networkdevices dir is there'''
        self.assertEqual(
            self.devices().find('"/dmd/Devices/NetworkDevices"') != -1, 1)

    def testSeeServers(self):
        '''test to see if the servers dir is there'''
        self.assertEqual(
            self.devices().find('"/dmd/Devices/Servers"') != -1, 1)

class NetworkDevicesListTest(unittest.TestCase):
    '''test the networkdevices directory'''
    devices = (makerequest.makerequest(Zope.app())).dmd.Devices.NetworkDevices.index_html
    
    def testSeeFirewall(self):
        '''make sure the firewall directory is visible'''
        self.assertEqual(
            self.devices().find('"/dmd/Devices/NetworkDevices/Firewall"') != -1, 1)

    def testSeeSwitch(self):
        '''make sure the switch directory is visible'''
        self.assertEqual(
            self.devices().find('"/dmd/Devices/NetworkDevices/Switch"') != -1, 1)

    def testSeeCableModem(self):
        '''make sure the cablemodem directory is visible'''
        self.assertEqual(
            self.devices().find('"/dmd/Devices/NetworkDevices/CableModem"') != -1, 1)

    def testSeeUBR(self):
        '''make sure the ubr directory is there'''
        self.assertEqual(
            self.devices().find('"/dmd/Devices/NetworkDevices/UBR"') != -1, 1)

    def testSeeRouter(self):
        '''make sure the router directory is there'''
        self.assertEqual(
            self.devices().find('"/dmd/Devices/NetworkDevices/Router"') != -1, 1)

class ServersListTest(unittest.TestCase):
    '''traverse the servers directory'''
    devices = (makerequest.makerequest(Zope.app())).dmd.Devices.Servers.index_html

    def testSeeLinux(self):
        '''make sure we see the linux directory'''
        self.assertEqual(
            self.devices().find('"/dmd/Devices/Servers/Linux"') != -1, 1)

    def testSeeSolaris(self):
        '''make sure we see the solaris directory'''
        self.assertEqual(
            self.devices().find('"/dmd/Devices/Servers/Solaris"') != -1, 1)

    def testSeeWindows(self):
        '''make sure we see the windows directory'''
        self.assertEqual(
            self.devices().find('"/dmd/Devices/Servers/Windows"') != -1, 1)

if __name__=="__main__":
    unittest.main()
