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

import logging
from cPickle import loads

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.DataCollector.ApplyDataMap import ApplyDataMap
from Products.DataCollector.plugins.zenoss.snmp.CiscoMap import CiscoMap


log = logging.getLogger("zen.testcases")


class TestCiscoMap(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.adm = ApplyDataMap()
        self.cmap = CiscoMap()
        self.device = self.dmd.Devices.createInstance('testDevice')


    def testNonAsciiSerial(self):
        results = loads("((dp1\nS'_snmpOid'\np2\nS'.1.3.6.1.4.1.9.1.414'\np3\nsS'setHWSerialNumber'\np4\nS'\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff'\np5\ns(dp6\nS'entPhysicalTable'\np7\n(dp8\nS'11'\np9\n(dp10\nS'serialNum'\np11\nS''\nssS'10'\np12\n(dp13\ng11\nS''\nssS'13'\np14\n(dp15\ng11\nS''\nssS'12'\np16\n(dp17\ng11\nS''\nssS'14'\np18\n(dp19\ng11\nS''\nssS'1'\n(dp20\ng11\nS''\nssS'3'\n(dp21\ng11\nS''\nssS'2'\n(dp22\ng11\nS''\nssS'5'\n(dp23\ng11\nS''\nssS'4'\n(dp24\ng11\nS''\nssS'7'\n(dp25\ng11\nS''\nssS'6'\n(dp26\ng11\nS''\nssS'9'\n(dp27\ng11\nS''\nssS'8'\n(dp28\ng11\nS''\nssstp29\n.")

        # Verify that the modeler plugin processes the data properly.
        om = self.cmap.process(self.device, results, log)
        self.assertEquals(om.setHWSerialNumber, 'Invalid')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestCiscoMap))
    return suite
