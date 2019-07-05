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
from mock import sentinel, patch, Mock

import types

from ..datamaps import (
    ZingDatamapHandler,
    ZingTxStateManager,
    ZFact,
    PLUGIN_NAME_ATTR,
)

from Products.DataCollector.plugins.DataMaps import ObjectMap
from Products.DataCollector.ApplyDataMap import IncrementalDataMap

from Products.ZenModel.Device import Device
from Products.Zing.interfaces import IObjectMapContextProvider

import transaction

PATH = {'src': 'Products.Zing.datamaps'}


class TestIncrementalDataMapHandler(TestCase):

    def setUp(t):
        # ZingTxState sets global variables on transact, clear it on each test
        transaction.abort()

        t.target = Mock(
            name='target_name',
            id='target_id',
            a1='attribute 1',
            dimension1='device d1',
            metadata1='device m1',
            isLockedFromUpdates=Mock(return_value=False),
            isLockedFromDeletion=Mock(return_value=False),
        )
        # get the target from the relationship
        t.relationship = Mock(
            name='relationship',
            spec_set=[t.target.id, '_getOb', 'hasobject', '_setObject']
        )
        setattr(t.relationship, t.target.id, t.target)
        t.relationship._getOb.return_value = t.target
        t.relname = 'relationship_name'
        # get the relationship on the parent
        t.parent = Mock(
            name='parent',
            spec_set=['id', t.relname, 'removeRelation', 'getUUID'],
        )
        setattr(t.parent, t.relname, t.relationship)
        t.compname = 'parent.path.may.be.long'
        # find the parent by its path from the base device
        t.base = Mock(Device, dmd=Mock())
        t.base.getObjByPath.return_value = t.parent
        # using special attributes specified on the ObjectMap
        t.object_map = ObjectMap({
            'id': t.target.id, 'relname': t.relname, 'compname': t.compname,
            PLUGIN_NAME_ATTR: 'test_plugin_name',
            "dimension2": "objectmap d2",
            "metadata2": "objectmap m2",
        })

        t.idm = IncrementalDataMap(t.base, t.object_map)

    @patch('{src}.subscribers'.format(**PATH), autospec=True)
    def test_generate_facts(t, subscribers):
        # registered event handlers
        subscribers.return_value = [
            ObjectMapContextProvider1(''), ObjectMapContextProvider2('')
        ]
        t.target.getDeviceClassName.return_value = 'getDeviceClassName'
        t.target.getDeviceGroupNames.return_value = 'getDeviceGroupNames'
        t.target.getLocationName.return_value = 'getLocationName'
        t.target.getSystemNames.return_value = 'getSystemNames'

        # ApplyDataMap side-effects, current implementation expects this
        for attr, value in t.idm.iteritems():
            setattr(t.target, attr, value)

        t.assertEqual(t.target.metadata2, 'objectmap m2')

        zdh = ZingDatamapHandler(Mock(name='dmd'))
        zdh.add_datamap(t.target, t.idm)
        zdh.add_context(t.idm, t.target)

        zing_tx_state = zdh._get_zing_tx_state()
        ret = zdh.generate_facts(zing_tx_state)

        subscribers.assert_called_with([t.target], IObjectMapContextProvider)
        t.assertIsInstance(ret, types.GeneratorType)
        t.maxDiff = None
        facts = [f for f in ret]

        t.assertEqual(
            {
                'name': t.target.titleOrId.return_value,
                'id': t.idm.id,
                'dimension2': 'objectmap d2',
                'metadata1': 'device m1',
                'metadata2': 'objectmap m2',
                'metadata3': ['omcp1 value3', 'omcp2 value3'],
                'metadata4': {'key3': 'omcp1 value4', 'key4': 'omcp2 value4'},
                'metadata5': 'omcp1 value5',
                'metadata6': 'omcp2 value6',
            },
            facts[0].data,  # AKA metadata
        )
        t.assertEqual(
            {
                ZFact.FactKeys.PLUGIN_KEY: 'test_plugin_name',
                'meta_type': t.target.meta_type,
                'contextUUID': t.target.getUUID.return_value,
                'parent': t.parent.getUUID.return_value,
                'relationship': t.relname,
                'dimension1': 'device d1',
                'dimension2': 'objectmap d2',
                'dimension3': 'omcp1 value3',
                'dimension4': 'omcp2 value4',
            },
            facts[0].metadata,  # AKA dimensions
        )
        t.assertEqual(
            {
                'device_class': t.target.getDeviceClassName.return_value,
                'groups': t.target.getDeviceGroupNames.return_value,
                'location': [t.target.getLocationName.return_value],
                'systems': t.target.getSystemNames.return_value,
            },
            facts[1].data,
        )
        t.assertEqual(
            {
                ZFact.FactKeys.PLUGIN_KEY: 'zen_organizers',
                'contextUUID': t.target.getUUID.return_value,
                'meta_type': t.target.meta_type,
            },
            facts[1].metadata,
        )
        t.assertEqual(
            {
                'name': t.target.titleOrId.return_value,
                'prod_state': t.target.getProductionStateString.return_value
            },
            facts[2].data,
        )
        t.assertEqual(
            {
                ZFact.FactKeys.PLUGIN_KEY: 'zen_device_info',
                'contextUUID': t.target.getUUID.return_value,
                'meta_type': t.target.meta_type,
            },
            facts[2].metadata,
        )

    @patch('{src}.subscribers'.format(**PATH), autospec=True)
    def test_generate_facts_handles_missing_parent_uuid(t, subscribers):
        # registered event handlers
        subscribers.return_value = [
            ObjectMapContextProvider1(''), ObjectMapContextProvider2('')
        ]
        t.target.getDeviceClassName.return_value = 'getDeviceClassName'
        t.target.getDeviceGroupNames.return_value = 'getDeviceGroupNames'
        t.target.getLocationName.return_value = 'getLocationName'
        t.target.getSystemNames.return_value = 'getSystemNames'

        # ApplyDataMap side-effects, current implementation expects this
        for attr, value in t.idm.iteritems():
            setattr(t.target, attr, value)

        t.assertEqual(t.target.metadata2, 'objectmap m2')

        zdh = ZingDatamapHandler(Mock(name='dmd'))
        zdh.add_datamap(t.target, t.idm)
        zdh.add_context(t.idm, t.target)

        t.parent.getUUID.side_effect = TypeError('404')

        zing_tx_state = zdh._get_zing_tx_state()
        ret = zdh.generate_facts(zing_tx_state)

        subscribers.assert_called_with([t.target], IObjectMapContextProvider)
        t.assertIsInstance(ret, types.GeneratorType)
        t.maxDiff = None
        facts = [f for f in ret]

        t.assertEqual(
            {
                ZFact.FactKeys.PLUGIN_KEY: 'test_plugin_name',
                'meta_type': t.target.meta_type,
                'contextUUID': t.target.getUUID.return_value,
                'relationship': t.relname,
                'dimension1': 'device d1',
                'dimension2': 'objectmap d2',
                'dimension3': 'omcp1 value3',
                'dimension4': 'omcp2 value4',
            },
            facts[0].metadata,  # AKA dimensions
        )
        t.assertNotIn('parent', facts[0].metadata)


class TestZingDatamapHandler(TestCase):

    def setUp(t):
        # ZingTxState sets global variables on transact, clear it on each test
        transaction.abort()
        t.context = sentinel.context
        t.zdh = ZingDatamapHandler(sentinel.context)

    def test___init__(t):
        t.assertEqual(t.zdh.context, sentinel.context)
        t.assertIsInstance(t.zdh.zing_tx_state_manager, ZingTxStateManager)

    @patch('{src}.ZingTxStateManager'.format(**PATH), autospec=True)
    def test__get_zing_tx_state(t, ZingTxStateManager):
        dmd = Mock(name='dmd')
        zdh = ZingDatamapHandler(dmd)

        ret = zdh._get_zing_tx_state()

        get_zing_tx_state = ZingTxStateManager.return_value.get_zing_tx_state
        t.assertEqual(ret, get_zing_tx_state.return_value)
        get_zing_tx_state.assert_called_with(dmd)

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

        zdh = ZingDatamapHandler(Mock('dmd'))
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
            {
                'device_class': 'test_device_class_name',
                'groups': [],
                'location': [],
                'systems': [],
            },
            facts[1].data,
        )
        t.assertEqual(
            {
                ZFact.FactKeys.PLUGIN_KEY: 'zen_organizers',
                'contextUUID': 'dummy_uuid',
                'meta_type': 'Device',
            },
            facts[1].metadata,
        )
        t.assertEqual(
            {
                'name': 'test_device',
                'prod_state': 'test_production_state_string'
            },
            facts[2].data,
        )
        t.assertEqual(
            {
                ZFact.FactKeys.PLUGIN_KEY: 'zen_device_info',
                'contextUUID': 'dummy_uuid',
                'meta_type': 'Device',
            },
            facts[2].metadata,
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
