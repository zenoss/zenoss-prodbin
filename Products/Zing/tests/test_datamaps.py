##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""Test Zing datamaps."""

from zope.component import getGlobalSiteManager

from Products.DataCollector.ApplyDataMap import ApplyDataMap
from Products.DataCollector.plugins.DataMaps import ObjectMap
from Products.ZenModel.Device import Device
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.Zing.interfaces import IObjectMapContextProvider


class TestZingDatamapHandler(BaseTestCase):
    def afterSetUp(self):
        self.adm = ApplyDataMap(datacollector="localhost")
        return super(TestZingDatamapHandler, self).afterSetUp()

    def beforeTearDown(self):
        gsm = getGlobalSiteManager()

        gsm.unregisterSubscriptionAdapter(
            ObjectMapContextProvider1,
            required=(CustomDevice,),
            provided=IObjectMapContextProvider)

        gsm.unregisterSubscriptionAdapter(
            ObjectMapContextProvider2,
            required=(CustomDevice,),
            provided=IObjectMapContextProvider)

        return super(TestZingDatamapHandler, self).beforeTearDown()

    def test_IObjectMapContextProvider(self):
        """Ensure IObjectMapContextProvider adapters are called."""
        gsm = getGlobalSiteManager()
        gsm.registerSubscriptionAdapter(
            ObjectMapContextProvider1,
            required=(CustomDevice,),
            provided=IObjectMapContextProvider)

        gsm.registerSubscriptionAdapter(
            ObjectMapContextProvider2,
            required=(CustomDevice,),
            provided=IObjectMapContextProvider)

        device = CustomDevice("device")
        self.dmd.Devices.devices._setObject(device.id, device)
        device = self.dmd.Devices.findDeviceByIdExact(device.id)
        device.dimension1 = "set"
        device.metadata1 = "set"

        adm = ApplyDataMap("localhost")
        adm.applyDataMap(
            device,
            ObjectMap({
                "dimension2": "modeled",
                "metadata2": "modeled",
            }))

        zdh = adm.zing_datamap_handler
        tx_state = zdh.zing_tx_state_manager.get_zing_tx_state(self.dmd)

        for fact in zdh.generate_facts(tx_state):
            dimensions = fact.metadata
            metadata = fact.data
            plugin = dimensions.get("plugin")

            if plugin != "Device":
                continue

            # Values already set in ZODB.
            self.assertEqual(dimensions["dimension1"], "set")
            self.assertEqual(metadata["metadata1"], "set")

            # Values in the ObjectMap.
            self.assertEqual(dimensions["dimension2"], "modeled")
            self.assertEqual(metadata["metadata2"], "modeled")

            # Values provided by a single adapter.
            self.assertEqual(dimensions["dimension3"], "value3")
            self.assertEqual(dimensions["dimension4"], "value4")
            self.assertEqual(metadata["metadata5"], "value5")
            self.assertEqual(metadata["metadata6"], "value6")

            # Concatenated lists from multiple adapters.
            self.assertEqual(
                metadata["metadata3"],
                ["value3", "value4"])

            # Merged dictionaries from multiple adapters.
            self.assertEqual(
                metadata["metadata4"],
                {"key3": "value3", "key4": "value4"})

            break
        else:
            self.fail("no matching fact found")


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


class ObjectMapContextProvider1(object):
    def __init__(self, obj):
        pass

    def get_dimensions(self, obj):
        return {
            "dimension1": obj.dimension1,
            "dimension2": obj.dimension2,
            "dimension3": "value3",
        }

    def get_metadata(self, obj):
        return {
            "metadata1": obj.metadata1,
            "metadata2": obj.metadata2,
            "metadata3": ["value3"],
            "metadata4": {"key3": "value3"},
            "metadata5": "value5",
        }


class ObjectMapContextProvider2(object):
    def __init__(self, obj):
        pass

    def get_dimensions(self, obj):
        return {
            "dimension4": "value4",
        }

    def get_metadata(self, obj):
        return {
            "metadata3": ["value4"],
            "metadata4": {"key4": "value4"},
            "metadata6": "value6",
        }


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestZingDatamapHandler))
    return suite
