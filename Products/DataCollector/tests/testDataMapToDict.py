##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging
from cPickle import loads

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.DataCollector.ApplyDataMap import ApplyDataMap
from Products.DataCollector.plugins.zenoss.snmp.NewDeviceMap \
    import NewDeviceMap
from Products.DataCollector.plugins.DataMaps \
    import RelationshipMap, ObjectMap, datamaps_to_dicts, dicts_to_datamaps

from Products.ZenUtils.Utils import prepId
log = logging.getLogger("zen.testcases")


class TestDataMapToDict(BaseTestCase):
    def afterSetUp(self):
        super(TestDataMapToDict, self).afterSetUp()
        self.adm = ApplyDataMap()
        self.ndmap = NewDeviceMap()
        self.device = self.dmd.Devices.createInstance('testDevice')

    def testWin2003Server(self):
        results = loads("((dp1\nS'snmpDescr'\np2\nS'Hardware: x86 Family 15 Model 4 Stepping 9 AT/AT COMPATIBLE - Software: Windows Version 5.2 (Build 3790 Uniprocessor Free)'\np3\nsS'snmpOid'\np4\nS'.1.3.6.1.4.1.311.1.1.3.1.2'\np5\ns(dtp6\n.")
        # Verify that the modeler plugin processes the data properly.
        om = self.ndmap.process(self.device, results, log)

        result_dict = {'modname': '',
                       'compname': '',
                       'snmpOid': '.1.3.6.1.4.1.311.1.1.3.1.2',
                       'setOSProductKey': 'Windows Version 5.2',
                       'classname': '',
                       'snmpDescr': 'Hardware: x86 Family 15 Model 4 Stepping 9 AT/AT COMPATIBLE - Software: Windows Version 5.2 (Build 3790 Uniprocessor Free)'}

        # Hard to compare tuples. so lets strip them out
        om_to_dict = {x: y for x, y in om.to_dict().iteritems() if x != 'setHWProductKey'}
        self.assertDictEqual(om_to_dict, result_dict)

        # Verify that a objectmap dict made it into the model properly.
        self.adm._applyDataMap(self.device, om.to_dict())
        self.assertEquals(self.device.getHWManufacturerName(), 'Microsoft')
        self.assertEquals(self.device.getHWProductName(),
                          '.1.3.6.1.4.1.311.1.1.3.1.2')
        self.assertEquals(self.device.getOSManufacturerName(),
                          'Unknown')
        self.assertEquals(self.device.getOSProductName(),
                          'Windows Version 5.2')
        self.assertEquals(self.device.snmpDescr,
                          'Hardware: x86 Family 15 Model 4 Stepping 9 AT/AT COMPATIBLE - Software: Windows Version 5.2 (Build 3790 Uniprocessor Free)')
        self.assertEquals(self.device.snmpOid,
                          '.1.3.6.1.4.1.311.1.1.3.1.2')

    def testCentOS5Server(self):
        results = loads("((dp1\nS'snmpDescr'\np2\nS'Linux centos32.damsel.loc 2.6.18-128.1.6.el5 #1 SMP Wed Apr 1 09:19:18 EDT 2009 i686'\np3\nsS'snmpOid'\np4\nS'.1.3.6.1.4.1.8072.3.2.10'\np5\ns(dtp6\n.")

        # Verify that the modeler plugin processes the data properly.
        om = self.ndmap.process(self.device, results, log)
        self.assertEquals(om.setHWProductKey.args[0],
                          '.1.3.6.1.4.1.8072.3.2.10')
        self.assertEquals(om.setHWProductKey.args[1],
                          'net snmp')
        self.assertEquals(om.setOSProductKey,
                          'Linux 2.6.18-128.1.6.el5')
        self.assertEquals(om.snmpDescr,
                          'Linux centos32.damsel.loc 2.6.18-128.1.6.el5 #1 SMP Wed Apr 1 09:19:18 EDT 2009 i686')
        self.assertEquals(om.snmpOid,
                          '.1.3.6.1.4.1.8072.3.2.10')

        # Verify that the data made it into the model properly.
        self.adm._applyDataMap(self.device, om.to_dict())
        self.assertEquals(self.device.getHWManufacturerName(),
                          'net snmp')
        self.assertEquals(self.device.getHWProductName(),
                          '.1.3.6.1.4.1.8072.3.2.10')
        self.assertEquals(self.device.getOSManufacturerName(),
                          'Unknown')
        self.assertEquals(self.device.getOSProductName(),
                          'Linux 2.6.18-128.1.6.el5')
        self.assertEquals(self.device.snmpDescr,
                          'Linux centos32.damsel.loc 2.6.18-128.1.6.el5 #1 SMP Wed Apr 1 09:19:18 EDT 2009 i686')
        self.assertEquals(self.device.snmpOid,
                          '.1.3.6.1.4.1.8072.3.2.10')

    def testSolaris(self):
        results = loads("((dp1\nS'snmpDescr'\np2\nS'SunOS testHost 5.10 Generic_138889-05 i86pc'\np3\nsS'snmpOid'\np4\nS'.1.3.6.1.4.1.8072.3.2.3'\np5\ns(dtp6\n.")

        # Verify that the modeler plugin processes the data properly.
        om = self.ndmap.process(self.device, results, log)

        # Verify that the data made it into the model properly.
        self.adm._applyDataMap(self.device, om.to_dict())
        self.assertEquals(self.device.getOSManufacturerName(),
                          'Sun')
        self.assertEquals(self.device.getOSProductName(),
                          'SunOS 5.10 Generic_138889-05')

    def testRelMapToDict(self):
        # Apply a RelMap with no interfaces

        interface_dict = {'modname': 'Products.ZenModel.IpInterface',
                          'compname': 'os',
                          'speed': 1000,
                          'id': prepId('eth0')
                          }

        om = ObjectMap()
        om.from_dict(interface_dict)

        relmap = RelationshipMap("interfaces", "os", "Products.ZenModel.IpInterface", objmaps=[om])

        results = relmap.to_dict()
        self.assertDictEqual(results,
                             {'modname': 'Products.ZenModel.IpInterface',
                              'relname': 'interfaces',
                              'compname': 'os',
                              'objmaps': [{'compname': 'os',
                                           'id': 'eth0',
                                           'modname': 'Products.ZenModel.IpInterface',
                                           'speed': 1000}],
                              'parentId': ''})

        # Verify that the data made it into the model properly.
        self.adm._applyDataMap(self.device, relmap.to_dict())
        self.assertEquals(self.device.os.interfaces()[0].id, 'eth0')
        self.assertEquals(self.device.os.interfaces()[0].speed, 1000)

        # Test the __len__ method
        self.assertEquals(len(relmap), 1)
        self.assertEquals(len(om), 4)

        # Test the __iter__ method
        self.assertEquals([x for x in relmap], [om])
        self.assertEquals(sorted([x for x in om]), sorted(['speed', 'id', 'modname', 'compname']))

        # Test the key lookup (ObjectMap)
        self.assertEquals(om['speed'], 1000)
        self.assertEquals(om.speed, 1000)

        # Test a Bad Key (ObjectMap)
        with self.assertRaises(KeyError) as keyException:
            om['speed1']

        # Test datamap_to_dicts
        datamap_list = [{'modname': 'Products.ZenModel.IpInterface',
                         'relname': 'interfaces',
                         'compname': 'os',
                         'objmaps': [{'speed': 1000,
                                      'modname': 'Products.ZenModel.IpInterface',
                                      'compname': 'os',
                                      'id': 'eth0'}
                                     ],
                         'parentId': ''}]
        self.assertEquals(datamaps_to_dicts(relmap), datamap_list)
        self.assertEquals(datamaps_to_dicts([relmap]), datamap_list)

        # Test dicts_to_datamap
        self.assertEquals(dicts_to_datamaps(datamap_list)[0].to_dict(), relmap.to_dict())

    def testRelMapToDictCoerceObjMaps(self):
        # Apply a RelMap with dict as an objmap

        interface_dict = {'modname': 'Products.ZenModel.IpInterface',
                          'compname': 'os',
                          'speed': 1000,
                          'id': prepId('eth0')
                          }

        relmap = RelationshipMap("interfaces", "os", "Products.ZenModel.IpInterface", objmaps=[interface_dict])

        results = relmap.to_dict()
        self.assertDictEqual(results,
                             {'modname': 'Products.ZenModel.IpInterface',
                              'relname': 'interfaces',
                              'compname': 'os',
                              'objmaps': [{'compname': 'os',
                                           'id': 'eth0',
                                           'modname': 'Products.ZenModel.IpInterface',
                                           'speed': 1000}],
                              'parentId': ''})

        # Verify that the data made it into the model properly.
        self.adm._applyDataMap(self.device, relmap.to_dict())
        self.assertEquals(self.device.os.interfaces()[0].id, 'eth0')
        self.assertEquals(self.device.os.interfaces()[0].speed, 1000)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestDataMapToDict))
    return suite
