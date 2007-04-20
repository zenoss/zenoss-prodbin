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

class ServiceAreaListTest(unittest.TestCase):
    '''test that we can navigate the serviceareas'''
    areas = (makerequest.makerequest(Zope.app())).dmd.ServiceAreas.index_html

    def testHasAnnapolis(self):
        '''make sure that annapolis is in the serviceareas'''
        self.assertEqual(
            self.areas().find('"/dmd/ServiceAreas/Annapolis"') != -1, 1)

class AnnapolisStatusTest(unittest.TestCase):
    '''test that the service area status page is ok'''
    areas = (makerequest.makerequest(Zope.app())).dmd.ServiceAreas.Annapolis.view

    def testKnowsName(self):
        '''make sure it knows who it is'''
        self.assertEqual(
            self.areas().find('Annapolis') != -1, 1)

    def testHasRouter(self):
        '''make sure it has router'''
        self.assertEqual(
            self.areas().find('"/dmd/Devices/NetworkDevices/Router/router.confmon.loc"') != -1, 1)

    def testHasEdahl04(self):
        '''make sure it has edahl04'''
        self.assertEqual(
            self.areas().find('"/dmd/Devices/Servers/Linux/edahl04.confmon.loc"') != -1, 1)

class AnnapolisTopTest(unittest.TestCase):
    '''make sure that the servicearea has the proper navbar'''
    areas = (makerequest.makerequest(Zope.app())).dmd.ServiceAreas.Annapolis.top

    def testHasStatus(self):
        '''make sure the status link is there'''
        self.assertEqual(
            self.areas().find('href="view"') != -1, 1)

    def testHasChanges(self):
        '''make sure the changes link is there'''
        self.assertEqual(
            self.areas().find('href="viewHistory"') != -1, 1)

if __name__=="__main__":
    unittest.main()
