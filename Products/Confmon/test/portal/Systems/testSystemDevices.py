#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__version__ = "$Revision: 1.1 $"[11:-2]

import unittest
import Zope
from Testing import makerequest

class GatewayDeviceTest(unittest.TestCase):
    '''test gateway's device screen'''
    system = (makerequest.makerequest(Zope.app())).dmd.Systems.Confmon.subsystems._getOb('Gateway').device_view

    def testIsGateway(self):
        '''look to make sure this is gateway'''
        self.assertEqual(
            self.system().find('Gateway') != -1, 1)

    def testHasEdahl(self):
        '''look for edahl04'''
        self.assertEqual(
            self.system().find('"/dmd/Devices/Servers/Linux/edahl04.confmon.loc"') != -1, 1)

    def testHasRouter(self):
        '''look for router'''
        self.assertEqual(
            self.system().find('"/dmd/Devices/NetworkDevices/Router/router.confmon.loc"') != -1, 1)

class ConfmonDeviceTest(unittest.TestCase):
    '''test confmon's device screen'''
    system = (makerequest.makerequest(Zope.app())).dmd.Systems._getOb('Confmon').device_view

    def testNoDevices(self):
        '''confmon shouldn't have any devices'''
        self.assertEqual(
            self.system().find('No Devices') != -1, 1)

if __name__=="__main__":
    unittest.main()
