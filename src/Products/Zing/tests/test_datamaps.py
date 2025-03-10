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


from ..datamaps import (
    ZingDatamapHandler,
    ZingTxStateManager,
)

from Products.ZenModel.Device import Device

import transaction

PATH = {'src': 'Products.Zing.datamaps'}


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
        ctx = Mock(device=Mock(return_value='target_device'))
        t.zdh.add_datamap(ctx, sentinel.datamap)
        zing_state = t.zdh._get_zing_tx_state()
        t.assertEqual(
            zing_state.datamaps, [(ctx.device.return_value, sentinel.datamap)]
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
