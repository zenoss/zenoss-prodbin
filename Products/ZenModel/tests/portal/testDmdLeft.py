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

__version__ = "$Revision: 1.1 $"[11:-2]

import unittest
import Zope
from Testing import makerequest

class DmdLeftTest(unittest.TestCase):
    '''check to see if the left frame is working'''
    request = (makerequest.makerequest(Zope.app())).dmd.left()
    
    def testHasIcon(self):
        '''test to see than the logo is at the top'''
        self.assertEqual(
            self.request.find('optimon_img') != -1, 1)

    def testHasCompanies(self):
        '''test to see that the companies directory exists'''
        self.assertEqual(
            self.request.find('href="Companies"') != -1, 1)

    def testHasDevices(self):
        '''test to see that the devices directory exists'''
        self.assertEqual(
            self.request.find('href="Devices"') != -1, 1)

    def testHasGroups(self):
        '''test to see that the groups dir exists'''
        self.assertEqual(
            self.request.find('href="Groups"') != -1, 1)

    def testHasLocations(self):
        '''test to see that the locations dir exists'''
        self.assertEqual(
            self.request.find('href="Locations"') != -1, 1)

    def testHasNetworks(self):
        '''test to see that the networks dir exists'''
        self.assertEqual(
            self.request.find('href="Networks"') != -1, 1)

    def testHasProducts(self):
        '''test to see that the products directory exists'''
        self.assertEqual(
            self.request.find('href="Products"') != -1, 1)

    def testHasServiceAreas(self):
        '''test to see that the serviceareas dir is here'''
        self.assertEqual(
            self.request.find('href="ServiceAreas"') != -1, 1)

    def testHasServices(self):
        '''test to see that the services link is present'''
        self.assertEqual(
            self.request.find('href="Services"') != -1, 1)

    def testHasSystems(self):
        '''test to see that the systems link is present'''
        self.assertEqual(
            self.request.find('href="Systems"') != -1, 1)

    def testHasMonitors(self):
        '''test to see if the monitors dir is here'''
        self.assertEqual(
            self.request.find('href="Monitors"') != -1, 1)

if __name__=="__main__":
    unittest.main()
