##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from unittest import TestCase
from mock import sentinel, patch

import types

from ..datamaps import (
    ZingDatamapHandler,
    ZingTxStateManager,
    ZFact,
    PLUGIN_NAME_ATTR,
)

from Products.DataCollector.plugins.DataMaps import ObjectMap
from Products.ZenModel.Device import Device
from Products.Zing.interfaces import IObjectMapContextProvider

PATH = {'src': 'Products.Zing.datamaps'}


class TestZingDatamapHandler(TestCase):

    def setUp(t):
        t.zdh = ZingDatamapHandler(sentinel.context)

    def test___init__(t):
        t.assertEqual(t.zdh.context, sentinel.context)
        t.assertIsInstance(t.zdh.zing_tx_state_manager, ZingTxStateManager)

    @patch('{src}.ZingTxStateManager'.format(**PATH), autospec=True)
    def test__get_zing_tx_state(t, ZingTxStateManager):
        zdh = ZingDatamapHandler(sentinel.context)

        ret = zdh._get_zing_tx_state()

        get_zing_tx_state = ZingTxStateManager.return_value.get_zing_tx_state
        t.assertEqual(ret, get_zing_tx_state.return_value)
        get_zing_tx_state.assert_called_with(sentinel.context)

    def test_add_datamap(t):
        t.zdh.add_datamap(sentinel.device, sentinel.datamap)
        zing_state = t.zdh._get_zing_tx_state()
        t.assertEqual(
            zing_state.datamaps, [(sentinel.device, sentinel.datamap)]
        )

    @patch('{src}.ObjectMapContext'.format(**PATH), autospec=True)
    def test_add_context(t, ObjectMapContext):
        t.zdh.add_context(sentinel.datamap, sentinel.device)
        zing_state = t.zdh._get_zing_tx_state()
        t.assertEqual(
            zing_state.datamaps_contexts[sentinel.datamap],
            ObjectMapContext.return_value
        )
        ObjectMapContext.assert_called_with(sentinel.device)

    @patch('{src}.subscribers'.format(**PATH), autospec=True)
    def test_generate_facts(t, subscribers):
        # registered event handlers
        subscribers.return_value = [
            ObjectMapContextProvider1(''), ObjectMapContextProvider2('')
        ]

        device = CustomDevice('test_device')
        device.dimension1 = 'device d1'
        device.metadata1 = 'device m1'

        objectmap = ObjectMap({
            PLUGIN_NAME_ATTR: 'test_plugin_name',
            "dimension2": "objectmap d2",
            "metadata2": "objectmap m2",
        })

        # ApplyDataMap side-effects, current implementation expects this
        for attr, value in objectmap.iteritems():
            setattr(device, attr, value)

        t.assertEqual(device.metadata2, 'objectmap m2')

        zdh = ZingDatamapHandler(sentinel.dmd)
        zdh.add_datamap(device, objectmap)
        zdh.add_context(objectmap, device)

        zing_tx_state = zdh._get_zing_tx_state()
        ret = zdh.generate_facts(zing_tx_state)

        subscribers.assert_called_with([device], IObjectMapContextProvider)
        t.assertIsInstance(ret, types.GeneratorType)
        t.maxDiff = None
        facts = [f for f in ret]
        t.assertEqual(
            {
                'name': 'test_device',
                'mem_capacity': 0,
                PLUGIN_NAME_ATTR: 'test_plugin_name',
                'dimension2': 'objectmap d2',
                'metadata1': 'device m1',
                'metadata2': 'objectmap m2',
                'metadata3': ['omcp1 value3', 'omcp2 value3'],
                'metadata4': {'key3': 'omcp1 value4', 'key4': 'omcp2 value4'},
                'metadata5': 'omcp1 value5',
                'metadata6': 'omcp2 value6',
            },
            facts[0].data,
        )
        t.assertEqual(
            {
                ZFact.FactKeys.PLUGIN_KEY: 'test_plugin_name',
                'meta_type': 'Device',
                'contextUUID': 'dummy_uuid',
                'dimension1': 'device d1',
                'dimension2': 'objectmap d2',
                'dimension3': 'omcp1 value3',
                'dimension4': 'omcp2 value4',
            },
            facts[0].metadata,
        )
        t.assertEqual(
            facts[1].data,
            {
                'device_class': 'test_device_class_name',
                'groups': [],
                'location': [],
                'systems': [],
            },
        )
        t.assertEqual(
            facts[1].metadata,
            {
                ZFact.FactKeys.PLUGIN_KEY: 'zen_organizers',
                'contextUUID': 'dummy_uuid',
                'meta_type': 'Device',
            },
        )
        t.assertEqual(
            facts[2].data,
            {
                'name': 'test_device',
                'prod_state': 'test_production_state_string'
            },
        )
        t.assertEqual(
            facts[2].metadata,
            {
                ZFact.FactKeys.PLUGIN_KEY: 'zen_device_info',
                'contextUUID': 'dummy_uuid',
                'meta_type': 'Device',
            },
        )


class CustomDevice(Device):
    dimension1 = None
    dimension2 = None
    metadata1 = None
    metadata2 = None

    _properties = Device._properties + (
        {"id": "dimension1", "type": "string"},
        {"id": "dimension2", "type": "string"},
        {"id": "metadata1", "type": "string"},
        {"id": "metadata2", "type": "string"},
    )

    def getUUID(self):
        return 'dummy_uuid'

    def getDeviceClassName(self):
        return 'test_device_class_name'

    def getProductionStateString(self):
        return 'test_production_state_string'


class ObjectMapContextProvider1(object):

    def __init__(self, noop):
        pass

    def get_dimensions(self, obj):
        return {
            "dimension1": obj.dimension1,
            "dimension2": obj.dimension2,
            "dimension3": "omcp1 value3",
        }

    def get_metadata(self, obj):
        print('ObjectMapContextProvider1.get_metadata')
        return {
            "metadata1": obj.metadata1,
            "metadata2": obj.metadata2,
            "metadata3": ["omcp1 value3"],
            "metadata4": {"key3": "omcp1 value4"},
            "metadata5": "omcp1 value5",
        }


class ObjectMapContextProvider2(object):

    def __init__(self, noop):
        pass

    def get_dimensions(self, obj):
        return {
            "dimension4": "omcp2 value4",
        }

    def get_metadata(self, obj):
        return {
            "metadata3": ["omcp2 value3"],
            "metadata4": {"key4": "omcp2 value4"},
            "metadata6": "omcp2 value6",
        }
