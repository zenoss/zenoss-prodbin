###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))
  
from Products.ZenModel.Exceptions import *

from Products.ZenModel.Location import Location
from ZenModelBaseTest import ZenModelBaseTest
  
class TestLocation(ZenModelBaseTest):

    def setUp(self):
        super(TestLocation, self).setUp()
        # Monkeypatch Location since it doesn't have access to page templates
        # via acquisition
        Location.mapTooltip = lambda *x:'PAGE TEMPLATE'

    def tearDown(self):
        # Remove the monkeypatch
        del Location.mapTooltip

    def testGoogleMapsData(self):
        a = self.dmd.Locations.createOrganizer('A')
        a.address = 'rome, italy'
        data = a.getGeomapData()
        self.assert_(isinstance(data, list))
        addr, color, path, tpl = data
        self.assertEqual(addr, 'rome, italy')
        self.assertEqual(path, '/zport/dmd/Locations/A')
        self.assertEqual(tpl, 'PAGE TEMPLATE')

        locdata = self.dmd.Locations.getChildGeomapData()
        # Make sure it's JSON
        self.assert_(isinstance(locdata, basestring))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestLocation))
    return suite

if __name__=="__main__":
    framework()
