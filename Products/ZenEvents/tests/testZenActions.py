###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import unittest
import Globals
import transaction

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenEvents.zenactions import BaseZenActions
from Products.ZenEvents.MySqlEventManager import MySqlEventManager


class MockLogger(object):

    def debug(self, *args, **kwargs):
        pass


class MockZenEventManager(MySqlEventManager):

    def __init__(self, dmd):
        self.dmd = dmd
        
    log = MockLogger()
    
    def _getDeviceIdsMatching(self, searchTerm, globSearch=True):
        """Stub for the filterDeviceName test
        """
        return ["testDevice"]


class MockZenActions(BaseZenActions):

    def __init__(self, dmd):
        self.dmd = dmd
        

    log = MockLogger()


class ZenActionsTest(BaseTestCase):

    def setUp(self):
        BaseTestCase.setUp(self)
        self.zenActions = MockZenActions(self.dmd)

    def tearDown(self):
        self.zenActions = None
        zem = self.dmd.ZenEventManager
        conn = zem.connect()
        try:
            curs = conn.cursor()
            curs.execute("truncate status")
            curs.execute("truncate detail")
            curs.execute("truncate log")
            curs.execute("truncate history")
        finally:
            zem.close(conn)
        BaseTestCase.tearDown(self)

    def testDescribe(self):
        stmt = 'SELECT * FROM status LIMIT 0'
        description = self.zenActions._describe(stmt)
        self.assertEqual(self.zenActions.lastCommand, stmt)

        for (name, 
             type_code, 
             display_size,
             internal_size, 
             precision, 
             scale, 
             null_ok) in description:
             
            self.assert_(isinstance(name, basestring), 
                          'name must be a string')

    def testFilterDeviceNameIgnoresNonDeviceSearches(self):
        """When we are not searching for a device
        the where clause should be exactly the same 
        """
        whereClause = "severity >= 4 and eventState = 0 and prodState = 1000"
        nwhere = self.zenActions.filterDeviceName(MockZenEventManager(self.dmd), whereClause)
        self.assertEqual(whereClause, nwhere)

    def testFilterDeviceNameFilterLike(self):
        """When we are searching for something like
        device LIKE '%foo%' we should query the catalog
        for devices like foo
        """
        whereClause = "(prodState = 1000) and (device like '%ubuntu%') and (eventState = 0) and (severity >= 0)"
        nwhere = self.zenActions.filterDeviceName(MockZenEventManager(self.dmd), whereClause)
        self.assertNotEqual(whereClause, nwhere)
        # make sure we didn't strip out everything
        self.assertTrue('severity' in nwhere)
        self.assertTrue('testDevice' in nwhere, 'make sure we got our list of devices from the catalog')

    def testFilterDeviceNameFilterNotLike(self):
        """When we are searching for something like
        device not LIKE '%foo%' we should query the catalog
        for devices that are nothing like foo
        """
        whereClause = "(prodState = 1000) and (device not like '%ubuntu%') and (eventState = 0) and (severity >= 0)"
        nwhere = self.zenActions.filterDeviceName(MockZenEventManager(self.dmd), whereClause)
        self.assertNotEqual(whereClause, nwhere)
        self.assertTrue('NOT IN' in nwhere)

    def testFilterDeviceNameFilterBeginsWith(self):
        """Searching for a string that "starts with" the phrase
        """
        whereClause = "(prodState = 1000) and (device like 'ubuntu%') and (eventState = 0) and (severity >= 0)"
        nwhere = self.zenActions.filterDeviceName(MockZenEventManager(self.dmd), whereClause)
        self.assertNotEqual(whereClause, nwhere)
        self.assertTrue('testDevice' in nwhere)

    def testFilterDeviceNameEquals(self):
        """ When (device = 'foo')
        """
        whereClause = "(prodState = 1000) and (device = 'ubuntu') and (eventState = 0) and (severity >= 0)"
        nwhere = self.zenActions.filterDeviceName(MockZenEventManager(self.dmd), whereClause)
        self.assertNotEqual(whereClause, nwhere)
        self.assertTrue("IN ('testDevice')" in nwhere)

    def testFilterDeviceNameNotEquals(self):
        """ When (device = 'foo')
        """
        whereClause = "(prodState = 1000) and (device != 'ubuntu') and (eventState = 0) and (severity >= 0)"
        nwhere = self.zenActions.filterDeviceName(MockZenEventManager(self.dmd), whereClause)
        self.assertNotEqual(whereClause, nwhere)
        self.assertTrue("NOT IN ('testDevice')" in nwhere)
    
    def testFilterDeviceNameMultipleSearchTerms(self):
        """ When (device = 'foo' or device like '%bar%'
        """
        whereClause = "(prodState = 1000) and (device like '%joseph%' or device like '%ubuntu%') and (eventState = 0) and (severity >= 4)"
        nwhere = self.zenActions.filterDeviceName(MockZenEventManager(self.dmd), whereClause)
        self.assertNotEqual(whereClause, nwhere)
        self.assertTrue("IN ('testDevice')" in nwhere)
        
    def testColumnNames(self):
        columnNames = self.zenActions._columnNames('status')
        for columnName in columnNames:
            self.assert_(isinstance(columnName, basestring),
                         'columnName must be a string')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    #suite.addTest(makeSuite(ZenActionsTest))
    suite.addTest(makeSuite(BaseTestCase))
    return suite
