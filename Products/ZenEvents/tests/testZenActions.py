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


class MockLogger(object):

    def debug(self, *args, **kwargs):
        pass


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

    def testColumnNames(self):
        columnNames = self.zenActions._columnNames('status')
        for columnName in columnNames:
            self.assert_(isinstance(columnName, basestring),
                         'columnName must be a string')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(ZenActionsTest))
    return suite
