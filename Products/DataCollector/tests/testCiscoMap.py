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
        results = loads("((dp0\nS'_serialNumber'\np1\nS'\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff'\np2\nsS'_memFree'\np3\nL690209880L\nsS'_memUsed'\np4\nL136548740L\nsS'snmpOid'\np5\nS'.1.3.6.1.4.1.9.1.222'\np6\ns(dp7\nS'entPhysicalTable'\np8\n(dp9\nstp10\n.")

        # Verify that the modeler plugin processes the data properly.
        om = self.cmap.process(self.device, results, log)[0]
        self.assertEquals(om.setHWSerialNumber, 'Invalid')


    def testTotalMemory(self):
        results = loads("((dp0\nS'_serialNumber'\np1\nS'\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff'\np2\nsS'_memFree'\np3\nL690209880L\nsS'_memUsed'\np4\nL136548740L\nsS'snmpOid'\np5\nS'.1.3.6.1.4.1.9.1.222'\np6\ns(dp7\nS'entPhysicalTable'\np8\n(dp9\nstp10\n.")

        om = self.cmap.process(self.device, results, log)[1]
        self.assertEquals(om.compname, 'hw')
        self.assertEquals(om.totalMemory, 826758620)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestCiscoMap))
    return suite
