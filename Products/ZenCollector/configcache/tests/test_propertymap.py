##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

from unittest import TestCase

from ..utils.propertymap import DevicePropertyMap


class EmptyBestMatchMapTest(TestCase):
    """Test an empty BestMatchMap object."""

    def setUp(t):
        t.bmm = DevicePropertyMap({}, None)

    def tearDown(t):
        del t.bmm

    def test_get(t):
        t.assertIsNone(t.bmm.get("/zport/dmd/Devices"))

    def test_smallest_value(t):
        t.assertIsNone(t.bmm.smallest_value())


class BestMatchMapTest(TestCase):
    """Test a BestMatchMap object."""

    mapping = {
        "/zport/dmd/Devices": 10,
        "/zport/dmd/Devices/Server/Linux": 11,
        "/zport/dmd/Devices/Server/SSH/Linux/devices/my-device": 12,
        "/zport/dmd/Devices/vSphere": 13,
        "/zport/dmd/Devices/Network": 14,
    }

    _default = 15

    def setUp(t):
        t.bmm = DevicePropertyMap(t.mapping, t._default)

    def tearDown(t):
        del t.bmm

    def test_get_root(t):
        value = t.bmm.get("/zport/dmd/Devices/Server-stuff/devices/dev2")
        t.assertEqual(10, value)

    def test_get_exact_match(t):
        value = t.bmm.get(
            "/zport/dmd/Devices/Server/SSH/Linux/devices/my-device"
        )
        t.assertEqual(12, value)

    def test_get_best_match(t):
        value = t.bmm.get("/zport/dmd/Devices/Server/Linux/devices/dev3")
        t.assertEqual(11, value)

    def test_get_too_short_request(t):
        value = t.bmm.get("/Devices")
        t.assertEqual(t._default, value)

    def test_smallest_value(t):
        value = t.bmm.smallest_value()
        t.assertEqual(10, value)
