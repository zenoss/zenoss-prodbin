#!/usr/bin/env python

##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import time
import Globals

from Products.ZenUtils.Utils import unused
from Testing import ZopeTestCase

import Products.ZenPackAdapter.db
from Products.ZenPackAdapter.db import DB
from Products.ZenPackAdapter.model import Device, DeviceClass

unused(Globals)


class TestZObject(ZopeTestCase.ZopeTestCase):

    def setUp(self):
        self.db = DB()
        self.db.load_classmodels()

        # override the default db with our testing one
        Products.ZenPackAdapter.db.get_db = lambda: self.db

        self.db.store_deviceclass(DeviceClass(
            id="/Test",
            zProperties={
                'zPythonClass': 'ZenPacks.zenoss.EMC.base.SMISProvider',
                'zTestPropertySetAtTest': 123,
                'zTestPropertyOverride': 'set at test',
            }
        ))

        self.db.store_device(Device(
            id="device1",
            device_class="/Test",
            manageIp="1.2.3.4",
            zProperties={
                'zTestPropertyLocal': 7,
                'zTestPropertyOverride': 'overridden'
            }

        ))

        self.db.index()

        mapper = self.db.get_mapper('device1')

        mapper.add(
            'device1', {
                'title': 'device1',
                'type': 'ZenPacks.zenoss.EMC.base.SMISProvider',
                'links': {
                    'arrays': set(['array1']),
                    'hw': set(['hw'])
                },
                'properties': {
                    'impactFromDimensions': [],
                    'impactToDimensions': [],
                    'wbemName': u'testingValue'
                }
            }
        )

        mapper.add(
            'array1', {
                'title': u'emc-vnx1',
                'type': 'ZenPacks.zenoss.EMC.base.Array',
                'links': {
                    'smis': set(['device1'])
                },
                'properties': {
                    'arrayName': u'emc-vnx1',
                    'arrayVersion': u'Rack Mounted VNX5200'
                }
            }
        )

        mapper.add(
            'hw', {
                'title': None,
                'type': 'ZenPacks.zenoss.StorageBase.Hardware',
                'links': {
                    'device': set(['device1']),
                    'enclosures': set(['enclosure1', 'enclosure2'])
                },
                'properties': {}
            }
        )

        mapper.add(
            'enclosure1', {
                'title': u'Shelf 0/0',
                'type': 'ZenPacks.zenoss.EMC.base.Enclosure',
                'links': {
                },
                'properties': {
                    'enclosureState': 'OK',
                }
            }
        )

        mapper.add(
            'enclosure2', {
                'title': u'Shelf 0/0',
                'type': 'ZenPacks.zenoss.EMC.base.Enclosure',
                'links': {
                },
                'properties': {
                    'enclosureState': 'OK',
                }
            }
        )

    def test_device_id(self):
        device = self.db.get_zobject('device1')
        self.assertEqual(device.id, 'device1')

    def test_component_id(self):
        component = self.db.get_zobject('device1', 'enclosure1')
        self.assertEqual(component.id, 'enclosure1')

    def test_meta_type(self):
        device = self.db.get_zobject('device1')
        component = self.db.get_zobject('device1', 'enclosure1')
        self.assertEqual(device.meta_type, 'SMISProvider')
        self.assertEqual(component.meta_type, 'EMCStorageEnclosure')

    def test_device_class(self):
        device = self.db.get_zobject('device1')
        self.assertEqual(device.device_class, '/Test')

    def test_device_os(self):
        # make sure that the os component exists, even though we didn't model it
        device = self.db.get_zobject('device1')
        self.assertIsNotNone(device.os)

    def test_zProperties_direct(self):
        device = self.db.get_zobject('device1')
        self.assertEqual(device.zTestPropertyLocal, 7)

    def test_zProperties_acquired_dc(self):
        device = self.db.get_zobject('device1')
        self.assertEqual(device.zTestPropertySetAtTest, 123)

    def test_zProperties_overridden_at_device(self):
        device = self.db.get_zobject('device1')
        self.assertEqual(device.zTestPropertyOverride, "overridden")

    def test_properties_direct(self):
        component = self.db.get_zobject('device1', 'array1')
        self.assertEqual(component.arrayName, "emc-vnx1")

    def test_properties_acquired_device(self):
        component = self.db.get_zobject('device1', 'array1')
        self.assertEqual(component.wbemName, "testingValue")

    def test_relationship_direct(self):
        device = self.db.get_zobject('device1')
        self.assertIsNotNone(device.hw)
        self.assertEqual(device.hw.id, 'hw')

    def test_relationship_toone(self):
        pass

    def test_relationship_tomany(self):
        device = self.db.get_zobject('device1')
        enclosure_ids = set(x.id for x in device.hw.enclosures())
        self.assertEqual(enclosure_ids, set(['enclosure1', 'enclosure2']))

    def test_devicemethod(self):
        device = self.db.get_zobject('device1')
        self.assertEqual(device.device().id, device.id)

        devicehw = self.db.get_zobject('device1').hw
        self.assertEqual(devicehw.device().id, device.id)

        component = self.db.get_zobject('device1', 'enclosure1')
        self.assertEqual(component.device().id, device.id)


    def test_getSubComponents(self):
        device = self.db.get_zobject('device1')
        components = list(device.getSubComponents())
        self.assertEquals(len(components), 5)

        component_ids = set([x.id for x in components])
        self.assertEquals(component_ids, set(
            ['array1', 'hw', 'os', 'enclosure1', 'enclosure2']
        ))

    def test_getMonitoredComponents(self):
        device = self.db.get_zobject('device1')
        components = list(device.getMonitoredComponents())
        self.assertEquals(len(components), 5)

        component_ids = set([x.id for x in components])
        self.assertEquals(component_ids, set(
            ['array1', 'hw', 'os', 'enclosure1', 'enclosure2']
        ))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestZObject))
    return suite


if __name__ == "__main__":
    from zope.testrunner.runner import Runner
    runner = Runner(found_suites=[test_suite()])
    runner.run()


