#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__version__ = "$Revision: 1.3 $"[11:-2]

import unittest
import Zope
from Testing import makerequest

class Edahl04StatusTest(unittest.TestCase):
    '''check the device status page for edahl04.confmon.loc'''
    status = (makerequest.makerequest(Zope.app())).dmd.Devices.Servers.Linux._getOb('edahl04.confmon.loc').view

    def testState(self):
        '''make sure edahl04 is pre-production'''
        self.assertEqual(
            self.status().find('Pre-Production') != -1, 1)

    def testHasManufacturer(self):
        '''make sure edahl04 was made by compaq'''
        self.assertEqual(
            self.status().find("'/dmd/Companies/Compaq'") != -1, 1)

    def testHasModel(self):
        '''make sure edahl04 is a deskpro'''
        self.assertEqual(
            self.status().find("'/dmd/Products/Hardware/Deskpro'") != -1, 1)

    def testHasLocation(self):
        '''make sure edahl04 is in Annapolis'''
        self.assertEqual(
            self.status().find("'/dmd/Locations/Annapolis'") != -1, 1)

    def testHasRack(self):
        '''make sure edahl04 is in the A1 rack'''
        self.assertEqual(
            self.status().find("'/dmd/Locations/Annapolis/racks/A1'") != -1, 1)

    def testInSystem(self):
        '''make sure edahl04 is in the Gateway system'''
        self.assertEqual(
            self.status().find('"/dmd/Systems/Confmon/subsystems/Gateway"') != -1, 1)

    def testInServiceArea(self):
        '''make sure edahl04 is in the annapolis ServiceArea'''
        self.assertEqual(
            self.status().find('"/dmd/ServiceAreas/Annapolis"') != -1, 1)

    def testInGroup(self):
        '''make sure edahl04 is in the development group'''
        self.assertEqual(
            self.status().find('"/dmd/Groups/Development"') != -1, 1)

    def testInMonitor(self):
        '''make sure edahl04 is being monitored by the default pingmonitor'''
        self.assertEqual(
            self.status().find('"/dmd/Monitors/StatusMonitors/Default"') != -1, 1)

    def testInNetwork(self):
        '''make sure edahl04 is in the 10.2.1.0 network'''
        self.assertEqual(
            self.status().find("'/dmd/Networks/10.2.1.0'") != -1, 1)

class RouterStatusTest(unittest.TestCase):
    '''check the device status page for router.confmon.loc'''
    status = (makerequest.makerequest(Zope.app())).dmd.Devices.NetworkDevices.Router._getOb('router.confmon.loc').view

    def testState(self):
        '''make sure router is pre-production'''
        self.assertEqual(
            self.status().find('Pre-Production') != -1, 1)

    def testHasManufacturer(self):
        '''make sure router was made by cisco'''
        self.assertEqual(
            self.status().find("'/dmd/Companies/Cisco'") != -1, 1)

    def testHasModel(self):
        '''make sure router is a 1600 series'''
        self.assertEqual(
            self.status().find("'/dmd/Products/Hardware/1602'") != -1, 1)

    def testHasLocation(self):
        '''make sure router is in Annapolis'''
        self.assertEqual(
            self.status().find("'/dmd/Locations/Annapolis'") != -1, 1)

    def testHasRack(self):
        '''make sure router is in the rack B43'''
        self.assertEqual(
            self.status().find("'/dmd/Locations/Annapolis/racks/B43'") != -1, 1)

    def testInSystem(self):
        '''make sure router is in the Gateway system'''
        self.assertEqual(
            self.status().find('"/dmd/Systems/Confmon/subsystems/Gateway"') != -1, 1)

    def testInServiceArea(self):
        '''make sure router is in the annapolis ServiceArea'''
        self.assertEqual(
            self.status().find('"/dmd/ServiceAreas/Annapolis"') != -1, 1)

    def testInGroup(self):
        '''make sure router is in the development group'''
        self.assertEqual(
            self.status().find('"/dmd/Groups/Development"') != -1, 1)

    def testInMonitor(self):
        '''make sure router is being monitored by the default pingmonitor'''
        self.assertEqual(
            self.status().find('"/dmd/Monitors/StatusMonitors/Default"') != -1, 1)

if __name__=="__main__":
    unittest.main()
