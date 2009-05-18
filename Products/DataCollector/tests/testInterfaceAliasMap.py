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
import os
from cPickle import load

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.DataCollector.ApplyDataMap import ApplyDataMap
from Products.DataCollector.plugins.zenoss.snmp.InterfaceAliasMap \
    import InterfaceAliasMap

log = logging.getLogger("zen.testcases")


class TestInterfaceAliasMap(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.adm = ApplyDataMap()
        self.iamap = InterfaceAliasMap()
        self.device = self.dmd.Devices.createInstance('testDevice')


    def testCisco3560(self):
        pickle = open("%s/data/InterfaceAliasMap_cisco3560.pickle" % \
            os.path.dirname(__file__), 'rb')
        results = load(pickle)
        pickle.close()
        
        # Verify that the modeler plugin processes the data properly.
        relmap = self.iamap.process(self.device, results, log)
        self.assertEquals(relmap.compname, 'os')
        self.assertEquals(relmap.relname, 'interfaces')
        self.assertEquals(len(relmap.maps), 58)
        
        om = relmap.maps[0]
        self.assertEquals(om.id, 'Vl1')
        self.assertEquals(om.description, 'Description of Vlan1')
        
        # Verify that the data made it into the model properly.
        self.adm._applyDataMap(self.device, relmap)
        iface = self.device.os.interfaces.Vl1
        self.assertEquals(iface.id, 'Vl1')
        self.assertEquals(iface.description, 'Description of Vlan1')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestInterfaceAliasMap))
    return suite
