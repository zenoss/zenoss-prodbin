##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
import os
from cPickle import load

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.DataCollector.ApplyDataMap import ApplyDataMap
from Products.DataCollector.plugins.zenoss.snmp.InterfaceAliasMap \
    import InterfaceAliasMap

log = logging.getLogger("zen.testcases")


class TestInterfaceAliasMap(BaseTestCase):
    def afterSetUp(self):
        super(TestInterfaceAliasMap, self).afterSetUp()
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
