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

        # This call doesn't block, but we can wait for the subprocess 
        # to finish.
        proc = zem.manage_deleteHistoricalEvents(agedDays=1)
        proc.wait()

        # Verify that the event, detail and log were all deleted.
        self.assertEquals(history_count, self._getEventCount('history'))
        self.assertEquals(detail_count, self._getEventCount('detail'))
        self.assertEquals(log_count, self._getEventCount('log'))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testEventMaintenance))
    return suite
