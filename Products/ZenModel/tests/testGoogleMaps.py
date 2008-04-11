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

from ZenModelBaseTest import ZenModelBaseTest

class DummyRequest(object):
    def __init__(self, dataz):
        from cStringIO import StringIO
        self._file = StringIO()
        self._file.write(dataz)
        self._file.seek(0)

class TestGoogleMaps(ZenModelBaseTest):

    def setUp(self):
        ZenModelBaseTest.setUp(self)
        self.dev = self.dmd.Devices.createInstance('testdev')
        self.loc = self.dmd.Locations.createOrganizer('annapolis')
        self.loc.address = 'Annapolis, MD'
        self.geocodedata = """
            {"Z":{"annapolis md":{"name":"Annapolis, MD", 
            "Status":{"code":610, "request":"geocode"}}}}
        """.strip()

    def testSetGeocodeCache(self):
        request = DummyRequest(self.geocodedata)
        self.dmd.setGeocodeCache(request)
        self.assert_(self.dmd.geocache == self.geocodedata)

    def testGetGeoCache(self):
        self.dmd.geocache = self.geocodedata
        testdata = self.dmd.getGeoCache()
        self.assert_('\\r' not in testdata)
        self.assert_('\\n' not in testdata)

    def testClearGeocodeCache(self):
        self.dmd.geocache = self.geocodedata
        self.dmd.clearGeocodeCache()
        self.assert_(not self.dmd.geocache)

    def testDummyTest(self):
        self.assert_("IAN IS JUST TESTING THE BUILDBOT"==False)

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestGoogleMaps))
    return suite
