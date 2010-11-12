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

import time
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenEvents.Exceptions import *

class testEventMaintenance(BaseTestCase):

    def _getEventCount(self, table):
        """
        Returns the number of rows in the specified table.
        """
        zem = self.dmd.ZenEventManager
        conn = zem.connect()
        count = None
        try:
            curs = conn.cursor()
            curs.execute('SELECT COUNT(*) FROM %s' % table)
            while 1:
                rows = curs.fetchmany()
                if not rows: break
                count = rows[0][0]
        finally:
            zem.close(conn)

        return count


    def testDeleteHistory(self):
        zem = self.dmd.ZenEventManager

        # Get initial row counts for comparison purposes.
        history_count = self._getEventCount('history')
        detail_count = self._getEventCount('detail')
        log_count = self._getEventCount('log')

        # Create old event with detail and log.
        evid = zem.sendEvent(dict(
            rcvtime=time.time() - (86400 * 7),
            device='testDevice',
            summary='test summary',
            severity=2,
            nonStandardField='test detail',
            ))
        zem.manage_deleteEvents((evid,))

        # Verify that the event, detail and log were added properly.
        self.assertEquals(history_count + 1, self._getEventCount('history'))
        self.assertEquals(detail_count + 1, self._getEventCount('detail'))
        self.assertEquals(log_count + 1, self._getEventCount('log'))

        proc = zem.manage_deleteHistoricalEvents(agedDays=1)

        # manage_deleteHistoricalEvents() does not block, but we have to
        # block for the test.
        proc.communicate()

        # verify that the history is <= current history since other events
        # could have been added this day
        self.assertTrue(self._getEventCount('history') <= history_count)
        self.assertTrue(self._getEventCount('detail') <= detail_count)
        self.assertTrue(self._getEventCount('log') <= log_count)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    #suite.addTest(makeSuite(testEventMaintenance))
    suite.addTest(makeSuite(BaseTestCase))
    return suite
