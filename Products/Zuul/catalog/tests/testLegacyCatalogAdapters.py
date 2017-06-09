##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import unittest

from Products.AdvancedQuery import And, Or, Not, Eq
from Products.ZenModel.IpInterface import manage_addIpInterface
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.Zuul.catalog.legacy import LegacyCatalogAdapter


DEVICE_CLASS = 'my_device_class_{}'
LOCATION = 'location_{}'
DEVICE = "my_device_{}"
MAC = '00:11:22:33:44:0{}'
IP = '10.10.10.{}/24'
NET = '10.10.10.0'


class MockDevice(object):
    def __init__(self):
        self.device_class = None
        self.location = None
        self.device = None
        self.interface = None
        self.ip = None


class TestLegacyCatalogAdapters(BaseTestCase):

    def afterSetUp(self):
        super(TestLegacyCatalogAdapters, self).afterSetUp()
        self.global_catalog = LegacyCatalogAdapter(self.dmd, "global_catalog")
        self.device_catalog = LegacyCatalogAdapter(self.dmd.Devices, "deviceSearch")
        self.layer2_catalog = LegacyCatalogAdapter(self.dmd, "layer2_catalog")
        self.layer3_catalog = LegacyCatalogAdapter(self.dmd, "layer3_catalog")
        self.ip_catalog     = LegacyCatalogAdapter(self.dmd.Networks, "ipSearch")

        self.n_devices = 5
        self.devices = {}
        for dev_id in xrange(self.n_devices):
            dev = MockDevice()
            dev.device_class = self.dmd.Devices.createOrganizer(DEVICE_CLASS.format(dev_id))
            dev.location = self.dmd.Locations.createOrganizer(LOCATION.format(dev_id))
            dev.device = dev.device_class.createInstance(DEVICE.format(dev_id))
            dev.device.setLocation("/".join(dev.location.getPrimaryPath())[10:])
            manage_addIpInterface(dev.device.os.interfaces, 'eth0', True)
            iface = dev.device.os.interfaces._getOb('eth0')
            iface._setPropValue('macaddress', MAC.format(dev_id))
            iface.addIpAddress(IP.format(dev_id))
            dev.ip = iface.ipaddresses()[0]
            dev.interface = iface
            self.devices[dev_id] = dev


    def validate_global_catalog(self):
        # Get Devices
        query = Eq("objectImplements", "Products.ZenModel.Device.Device")
        brains = self.global_catalog.search(query)
        self.assertEqual(len(brains), self.n_devices)

        # Get Locations
        query = Eq("objectImplements", "Products.ZenModel.Location.Location")
        brains = self.global_catalog.search(query)
        self.assertEqual(len(brains), self.n_devices + 1) # n_devices plus root node

        # Get Devices or IpAddresses
        query = []
        query.append(Eq("objectImplements", "Products.ZenModel.Device.Device"))
        query.append(Eq("objectImplements", "Products.ZenModel.IpAddress.IpAddress"))
        brains = self.global_catalog.search(Or(*query))
        self.assertEqual(len(brains), 2*self.n_devices)

        # Get a device by uid
        d = self.devices[0]
        uid = "/".join(d.device.getPrimaryPath())
        # global_catalog strips /zport/dmd/
        uid = uid[10:]
        brains = self.global_catalog.search(Eq("uid", uid))
        self.assertEqual(len(brains), 1) # not working


    def validate_device_catalog(self):
        # get all devices
        brains = self.device_catalog()
        self.assertEqual(len(brains), self.n_devices)

        # Grab a device a perform diferent searches
        d = self.devices[0]
        #  by uid
        uid = "/".join(d.device.getPrimaryPath())
        brains = self.device_catalog.search(Eq("uid", uid))
        self.assertEqual(len(brains), 1)
        #  by titleOrId
        titleOrId = d.device.id
        self.assertEqual(len(self.device_catalog.search(Eq("titleOrId", titleOrId))), 1)
        # by getDeviceIp
        ip = d.ip.id
        self.assertEqual(len(self.device_catalog.search(Eq("getDeviceIp", ip))), 1)

    def test_legacy_catalogs(self):
        self.validate_global_catalog()
        self.validate_device_catalog()



def test_suite():
    return unittest.TestSuite((unittest.makeSuite(TestLegacyCatalogAdapters),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
