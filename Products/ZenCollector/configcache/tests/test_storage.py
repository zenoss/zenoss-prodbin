##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import collections

from unittest import TestCase

from Products.ZenCollector.services.config import DeviceProxy
from Products.Jobber.tests.utils import subTest, RedisLayer

from ..cache.storage import ConfigStore
from ..cache import (
    ConfigKey,
    ConfigQuery,
    ConfigRecord,
    ConfigStatus,
)


_fields = collections.namedtuple(
    "_fields", "service monitor device uid updated"
)


class EmptyConfigStoreTest(TestCase):
    """Test an empty ConfigStore object."""

    layer = RedisLayer

    def setUp(t):
        t.store = ConfigStore(t.layer.redis)

    def tearDown(t):
        del t.store

    def test_search(t):
        t.assertIsInstance(t.store.search(), collections.Iterable)
        t.assertTupleEqual(tuple(t.store.search()), ())

    def test_get_with_default_default(t):
        key = ConfigKey("a", "b", "c")
        t.assertIsNone(t.store.get(key))

    def test_get_with_nondefault_default(t):
        key = ConfigKey("a", "b", "c")
        dflt = object()
        t.assertEqual(t.store.get(key, dflt), dflt)

    def test_remove(t):
        t.assertIsNone(t.store.remove())

    def test_get_status_no_keys(t):
        result = t.store.get_status()
        t.assertIsInstance(result, collections.Iterable)
        t.assertTupleEqual(tuple(result), ())

    def test_get_status_unknown_key(t):
        key = ConfigKey("a", "b", "c")
        result = t.store.get_status(key)
        t.assertIsInstance(result, collections.Iterable)
        t.assertTupleEqual(tuple(result), ())

    def test_get_pending(t):
        result = t.store.get_pending()
        t.assertIsInstance(result, collections.Iterable)
        t.assertTupleEqual(tuple(result), ())

    def test_get_older(t):
        result = t.store.get_older(1.0)
        t.assertIsInstance(result, collections.Iterable)
        t.assertTupleEqual(tuple(result), ())

    def test_get_newer(t):
        result = t.store.get_newer(1.0)
        t.assertIsInstance(result, collections.Iterable)
        t.assertTupleEqual(tuple(result), ())

    def test_search_badarg(t):
        with t.assertRaises(TypeError):
            t.store.search("blargh")


class _BaseTest(TestCase):
    # Base class to share setup code

    layer = RedisLayer

    fields = (
        _fields("a", "b", "c1", "/c1", 1234500.0),
        _fields("a", "b", "c2", "/c1", 1234550.0),
    )

    def setUp(t):
        DeviceProxy.__eq__ = _compare_configs
        t.store = ConfigStore(t.layer.redis)
        t.config1 = _make_config("test1", "_test1", "abc-test-01")
        t.config2 = _make_config("test2", "_test2", "abc-test-02")
        t.record1 = ConfigRecord.make(
            t.fields[0].service,
            t.fields[0].monitor,
            t.fields[0].device,
            t.fields[0].uid,
            t.fields[0].updated,
            t.config1,
        )
        t.record2 = ConfigRecord.make(
            t.fields[1].service,
            t.fields[1].monitor,
            t.fields[1].device,
            t.fields[1].uid,
            t.fields[1].updated,
            t.config2,
        )

    def tearDown(t):
        del t.store
        del t.config1
        del t.config2
        del t.record1
        del t.record2
        del DeviceProxy.__eq__


class ConfigStoreAddTest(_BaseTest):
    """Test the `add` method of ConfigStore."""

    def test_add_new_config(t):
        t.store.add(t.record1)
        t.store.add(t.record2)
        expected1 = ConfigKey(
            t.fields[0].service,
            t.fields[0].monitor,
            t.fields[0].device,
        )
        expected2 = ConfigKey(
            t.fields[1].service,
            t.fields[1].monitor,
            t.fields[1].device,
        )
        result = tuple(t.store.search())
        t.assertEqual(2, len(result))
        t.assertIn(expected1, result)
        t.assertIn(expected2, result)

        result = t.store.get(t.record1.key)
        t.assertIsInstance(result, ConfigRecord)
        t.assertEqual(t.record1, result)

        result = t.store.get(t.record2.key)
        t.assertIsInstance(result, ConfigRecord)
        t.assertEqual(t.record2, result)


class ConfigStoreSearchTest(_BaseTest):
    """Test the `search` method of ConfigStore."""

    def test_negative_search(t):
        t.store.add(t.record1)
        cases = (
            {"service": "x"},
            {"service": "x", "monitor": "y"},
            {"service": "x", "monitor": "y", "device": "z"},
            {"monitor": "y"},
            {"monitor": "y", "device": "z"},
            {"device": "z"},
        )
        for case in cases:
            with subTest(key=case):
                result = tuple(t.store.search(ConfigQuery(**case)))
                t.assertTupleEqual((), result)

    def test_positive_search_single(t):
        t.store.add(t.record1)
        f0 = t.fields[0]
        cases = (
            {"service": f0.service},
            {"service": f0.service, "monitor": f0.monitor},
            {
                "service": f0.service,
                "monitor": f0.monitor,
                "device": f0.device,
            },
            {"monitor": f0.monitor},
            {"monitor": f0.monitor, "device": f0.device},
            {"device": f0.device},
        )
        for case in cases:
            with subTest(key=case):
                result = tuple(t.store.search(ConfigQuery(**case)))
                t.assertTupleEqual((t.record1.key,), result)

    def test_positive_search_multiple(t):
        t.store.add(t.record1)
        t.store.add(t.record2)
        f0 = t.fields[0]
        cases = (
            ({"service": f0.service}, 2),
            ({"service": f0.service, "monitor": f0.monitor}, 2),
            (
                {
                    "service": f0.service,
                    "monitor": f0.monitor,
                    "device": f0.device,
                },
                1,
            ),
            ({"monitor": f0.monitor}, 2),
            ({"monitor": f0.monitor, "device": f0.device}, 1),
            ({"device": f0.device}, 1),
        )
        for args, count in cases:
            with subTest(key=args):
                result = tuple(t.store.search(ConfigQuery(**args)))
                t.assertEqual(count, len(result))


class ConfigStoreGetStatusTest(_BaseTest):
    """Test the `get_status` method of ConfigStore."""

    def test_get_status(t):
        t.store.add(t.record1)
        t.store.add(t.record2)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.fields[0].updated, status.updated)

        result = tuple(t.store.get_status(t.record2.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record2.key, key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.fields[1].updated, status.updated)


class ConfigStoreGetOlderTest(_BaseTest):
    """Test the `get_older` method of ConfigStore."""

    def test_get_older_less_single(t):
        t.store.add(t.record1)
        result = tuple(t.store.get_older(t.record1.updated - 1))
        t.assertEqual(0, len(result))

    def test_get_older_less_multiple(t):
        t.store.add(t.record1)
        t.store.add(t.record2)

        result = tuple(t.store.get_older(t.record1.updated - 1))
        t.assertEqual(0, len(result))

        result = tuple(t.store.get_older(t.record2.updated - 1))
        key, status = result[0]
        t.assertEqual(1, len(result))
        t.assertEqual(t.record1.key, key)
        t.assertEqual(t.record1.updated, status.updated)

    def test_get_older_equal_single(t):
        t.store.add(t.record1)
        result = tuple(t.store.get_older(t.record1.updated))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record1.updated, status.updated)

    def test_get_older_equal_multiple(t):
        t.store.add(t.record1)
        t.store.add(t.record2)

        result = tuple(t.store.get_older(t.record1.updated))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record1.updated, status.updated)

        result = sorted(
            t.store.get_older(t.record2.updated), key=lambda x: x[1].updated
        )
        t.assertEqual(2, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record1.updated, status.updated)

        key, status = result[1]
        t.assertEqual(t.record2.key, key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record2.updated, status.updated)

    def test_get_older_greater_single(t):
        t.store.add(t.record1)
        result = tuple(t.store.get_older(t.record1.updated + 1))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record1.updated, status.updated)

    def test_get_older_greater_multiple(t):
        t.store.add(t.record1)
        t.store.add(t.record2)

        result = tuple(t.store.get_older(t.record1.updated + 1))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record1.updated, status.updated)

        result = sorted(
            t.store.get_older(t.record2.updated + 1),
            key=lambda x: x[1].updated,
        )
        t.assertEqual(2, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record1.updated, status.updated)

        key, status = result[1]
        t.assertEqual(t.record2.key, key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record2.updated, status.updated)


class ConfigStoreGetNewerTest(_BaseTest):
    """Test the `get_newer` method of ConfigStore."""

    def test_get_newer_less_single(t):
        t.store.add(t.record1)
        result = tuple(t.store.get_newer(t.record1.updated - 1))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record1.updated, status.updated)

    def test_get_newer_less_multiple(t):
        t.store.add(t.record1)
        t.store.add(t.record2)

        result = sorted(
            t.store.get_newer(t.record1.updated - 1),
            key=lambda x: x[1].updated,
        )
        t.assertEqual(2, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record1.updated, status.updated)
        key, status = result[1]
        t.assertEqual(t.record2.key, key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record2.updated, status.updated)

    def test_get_newer_equal_single(t):
        t.store.add(t.record1)
        result = tuple(t.store.get_newer(t.record1.updated))
        t.assertEqual(0, len(result))

    def test_get_newer_equal_multiple(t):
        t.store.add(t.record1)
        t.store.add(t.record2)

        result = tuple(t.store.get_newer(t.record1.updated))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record2.key, key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record2.updated, status.updated)

    def test_get_newer_greater_single(t):
        t.store.add(t.record1)
        result = tuple(t.store.get_newer(t.record1.updated + 1))
        t.assertEqual(0, len(result))

    def test_get_newer_greater_multiple(t):
        t.store.add(t.record1)
        t.store.add(t.record2)
        result = tuple(t.store.get_newer(t.record1.updated + 1))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record2.key, key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record2.updated, status.updated)


class TestRetiredStatus(_BaseTest):
    """
    Test APIs regarding the ConfigStatus.Retired status.
    """

    def test_set_retired(t):
        t.store.add(t.record1)
        expected = (t.record1.key,)

        actual = t.store.set_retired(t.record1.key)
        t.assertTupleEqual(expected, actual)

    def test_set_retired_twice(t):
        t.store.add(t.record1)
        expected = ()

        t.store.set_retired(t.record1.key)
        actual = t.store.set_retired(t.record1.key)
        t.assertTupleEqual(expected, actual)

    def test_retired_status(t):
        t.store.add(t.record1)
        t.store.set_retired(t.record1.key)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Retired)
        t.assertEqual(status.updated, t.record1.updated)

    def test_get_retired(t):
        t.store.add(t.record1)
        t.store.set_retired(t.record1.key)

        result = tuple(t.store.get_retired())
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Retired)
        t.assertEqual(status.updated, t.record1.updated)


class TestExpiredStatus(_BaseTest):
    """
    Test APIs regarding the ConfigStatus.Expired status.
    """

    def test_set_expired(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 500

        expected = (t.record1.key,)
        actual = t.store.set_expired((t.record1.key, ts))
        t.assertTupleEqual(expected, actual)

    def test_set_expired_twice(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 500

        expected = ()

        t.store.set_expired((t.record1.key, ts))
        actual = t.store.set_expired((t.record1.key, ts))
        t.assertTupleEqual(expected, actual)

    def test_expired_status(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 500
        t.store.set_expired((t.record1.key, ts))

        result = tuple(t.store.get_status(t.record1.key))

        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Expired)

    def test_get_expired(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 500
        t.store.set_expired((t.record1.key, ts))

        result = tuple(t.store.get_expired())
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Expired)

    def test_expired_is_not_older(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 500
        t.store.set_expired((t.record1.key, ts))

        result = tuple(t.store.get_older(t.record1.updated))
        t.assertEqual(0, len(result))


class TestPendingStatus(_BaseTest):
    """
    Test APIs regarding the ConfigStatus.Pending status.
    """

    def test_set_pending(t):
        t.store.add(t.record1)
        submitted = t.record1.updated + 500
        expected = (t.record1.key,)

        actual = t.store.set_pending((t.record1.key, submitted))
        t.assertTupleEqual(expected, actual)

        expired_keys = tuple(t.store.get_expired())
        t.assertTupleEqual((), expired_keys)

        retired_keys = tuple(t.store.get_retired())
        t.assertTupleEqual((), retired_keys)

    def test_set_pending_twice(t):
        t.store.add(t.record1)
        submitted = t.record1.updated + 500
        expected = ()

        t.store.set_pending((t.record1.key, submitted))
        actual = t.store.set_pending((t.record1.key, submitted))
        t.assertTupleEqual(expected, actual)

    def test_pending_status(t):
        t.store.add(t.record1)
        submitted = t.record1.updated + 500
        t.store.set_pending((t.record1.key, submitted))

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Pending)
        t.assertEqual(submitted, status.submitted)

    def test_get_pending(t):
        t.store.add(t.record1)
        submitted = t.record1.updated + 500
        t.store.set_pending((t.record1.key, submitted))

        result = tuple(t.store.get_pending())
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Pending)
        t.assertEqual(submitted, status.submitted)

    def test_pending_is_not_older(t):
        t.store.add(t.record1)
        submitted = t.record1.updated + 500
        t.store.set_pending((t.record1.key, submitted))

        result = tuple(t.store.get_older(t.record1.updated))
        t.assertEqual(0, len(result))


class TestBuildingStatus(_BaseTest):
    """
    Test APIs regarding the ConfigStatus.Building status.
    """

    def test_set_building(t):
        t.store.add(t.record1)
        started = t.record1.updated + 500
        expected = (t.record1.key,)

        t.store.set_pending((t.record1.key, started - 100))
        actual = t.store.set_building((t.record1.key, started))
        t.assertTupleEqual(expected, actual)

        pending_keys = tuple(t.store.get_pending())
        t.assertTupleEqual((), pending_keys)

        expired_keys = tuple(t.store.get_expired())
        t.assertTupleEqual((), expired_keys)

        retired_keys = tuple(t.store.get_retired())
        t.assertTupleEqual((), retired_keys)

    def test_set_building_twice(t):
        t.store.add(t.record1)
        started = t.record1.updated + 500
        expected = ()

        t.store.set_building((t.record1.key, started))
        actual = t.store.set_building((t.record1.key, started))
        t.assertTupleEqual(expected, actual)

    def test_building_status(t):
        t.store.add(t.record1)
        started = t.record1.updated + 500
        t.store.set_building((t.record1.key, started))

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Building)
        t.assertEqual(started, status.started)

    def test_get_building(t):
        t.store.add(t.record1)
        started = t.record1.updated + 500
        t.store.set_building((t.record1.key, started))

        result = tuple(t.store.get_building())
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Building)
        t.assertEqual(started, status.started)

    def test_building_is_not_older(t):
        t.store.add(t.record1)
        started = t.record1.updated + 500
        t.store.set_building((t.record1.key, started))

        result = tuple(t.store.get_older(t.record1.updated))
        t.assertEqual(0, len(result))


class TestExpiredTransitions(_BaseTest):
    """
    Test transitions to and from ConfigStatus.Expired.
    """

    def test_retired_to_expired(t):
        t.store.add(t.record1)
        t.store.set_retired(t.record1.key)
        ts = t.record1.updated + 300

        expired_keys = t.store.set_expired((t.record1.key, ts))
        t.assertTupleEqual((t.record1.key,), expired_keys)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Expired)

        retired_keys = tuple(t.store.get_retired())
        t.assertTupleEqual((), retired_keys)

    def test_expired_to_retired(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 300
        t.store.set_expired((t.record1.key, ts))
        retired_keys = t.store.set_retired(t.record1.key)
        t.assertTupleEqual((t.record1.key,), retired_keys)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Retired)
        t.assertEqual(t.record1.updated, status.updated)


class TestPendingTransitions(_BaseTest):
    """
    Test transitions to and from ConfigStatus.Pending.
    """

    def test_current_to_pending(t):
        t.store.add(t.record1)
        submitted = t.record1.updated + 500

        pending_keys = t.store.set_pending((t.record1.key, submitted))
        t.assertTupleEqual((t.record1.key,), pending_keys)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Pending)
        t.assertEqual(submitted, status.submitted)

    def test_retired_to_pending(t):
        t.store.add(t.record1)
        t.store.set_retired(t.record1.key)
        submitted = t.record1.updated + 500

        pending_keys = t.store.set_pending((t.record1.key, submitted))
        t.assertTupleEqual((t.record1.key,), pending_keys)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Pending)
        t.assertEqual(submitted, status.submitted)

    def test_expired_to_pending(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 300
        submitted = t.record1.updated + 500
        t.store.set_expired((t.record1.key, ts))
        pending_keys = t.store.set_pending((t.record1.key, submitted))
        t.assertTupleEqual((t.record1.key,), pending_keys)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Pending)

        expired_keys = tuple(t.store.get_expired())
        t.assertTupleEqual((), expired_keys)

        retired_keys = tuple(t.store.get_retired())
        t.assertTupleEqual((), retired_keys)

        building_keys = tuple(t.store.get_building())
        t.assertTupleEqual((), building_keys)

    def test_pending_to_expired(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 300
        submitted = t.record1.updated + 500
        t.store.set_pending((t.record1.key, submitted))

        expired_keys = t.store.set_expired((t.record1.key, ts))
        t.assertTupleEqual((t.record1.key,), expired_keys)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Expired)
        t.assertEqual(ts, status.expired)

    def test_pending_to_retired(t):
        t.store.add(t.record1)
        submitted = t.record1.updated + 500
        t.store.set_pending((t.record1.key, submitted))

        retired_keys = t.store.set_retired(t.record1.key)
        t.assertTupleEqual((t.record1.key,), retired_keys)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Retired)
        t.assertEqual(t.record1.updated, status.updated)


class TestBuildingTransitions(_BaseTest):
    """
    Test transitions to and from ConfigStatus.Building.
    """

    def test_current_to_building(t):
        t.store.add(t.record1)
        started = t.record1.updated + 500

        building_keys = t.store.set_building((t.record1.key, started))
        t.assertTupleEqual((t.record1.key,), building_keys)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Building)
        t.assertEqual(started, status.started)

        pending_keys = tuple(t.store.get_pending())
        t.assertTupleEqual((), pending_keys)

        expired_keys = tuple(t.store.get_expired())
        t.assertTupleEqual((), expired_keys)

        retired_keys = tuple(t.store.get_retired())
        t.assertTupleEqual((), retired_keys)

    def test_retired_to_building(t):
        t.store.add(t.record1)
        t.store.set_retired(t.record1.key)
        started = t.record1.updated + 500

        building_keys = t.store.set_building((t.record1.key, started))
        t.assertTupleEqual((t.record1.key,), building_keys)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Building)
        t.assertEqual(started, status.started)

        pending_keys = tuple(t.store.get_pending())
        t.assertTupleEqual((), pending_keys)

        expired_keys = tuple(t.store.get_expired())
        t.assertTupleEqual((), expired_keys)

        retired_keys = tuple(t.store.get_retired())
        t.assertTupleEqual((), retired_keys)

    def test_expired_to_building(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 300
        started = t.record1.updated + 500
        t.store.set_expired((t.record1.key, ts))

        building_keys = t.store.set_building((t.record1.key, started))
        t.assertTupleEqual((t.record1.key,), building_keys)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Building)
        t.assertEqual(started, status.started)

        pending_keys = tuple(t.store.get_pending())
        t.assertTupleEqual((), pending_keys)

        expired_keys = tuple(t.store.get_expired())
        t.assertTupleEqual((), expired_keys)

        retired_keys = tuple(t.store.get_retired())
        t.assertTupleEqual((), retired_keys)

    def test_pending_to_building(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 300
        started = t.record1.updated + 500
        t.store.set_expired((t.record1.key, ts))
        t.store.set_pending((t.record1.key, started - 100))

        building_keys = t.store.set_building((t.record1.key, started))
        t.assertTupleEqual((t.record1.key,), building_keys)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Building)
        t.assertEqual(started, status.started)

        pending_keys = tuple(t.store.get_pending())
        t.assertTupleEqual((), pending_keys)

        expired_keys = tuple(t.store.get_expired())
        t.assertTupleEqual((), expired_keys)

        retired_keys = tuple(t.store.get_retired())
        t.assertTupleEqual((), retired_keys)

    def test_building_to_pending(t):
        t.store.add(t.record1)
        submitted = t.record1.updated + 300
        started = t.record1.updated + 500
        t.store.set_building((t.record1.key, started))

        pending_keys = t.store.set_pending((t.record1.key, submitted))
        t.assertTupleEqual((t.record1.key,), pending_keys)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Pending)
        t.assertEqual(submitted, status.submitted)

    def test_building_to_expired(t):
        t.store.add(t.record1)
        expired = t.record1.updated + 300
        started = t.record1.updated + 500
        t.store.set_building((t.record1.key, started))

        expired_keys = t.store.set_expired((t.record1.key, expired))
        t.assertTupleEqual((t.record1.key,), expired_keys)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Expired)
        t.assertEqual(expired, status.expired)

    def test_building_to_retired(t):
        t.store.add(t.record1)
        started = t.record1.updated + 500
        t.store.set_building((t.record1.key, started))

        retired_keys = t.store.set_retired(t.record1.key)
        t.assertTupleEqual((t.record1.key,), retired_keys)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Retired)
        t.assertEqual(t.record1.updated, status.updated)


class TestAddTransitions(_BaseTest):
    """
    Test status changes after adding a config.
    """

    def test_add_overwrites_retired(t):
        t.store.add(t.record1)
        t.store.set_retired(t.record1.key)
        t.store.add(t.record1)

        retired_keys = tuple(t.store.get_retired())
        t.assertTupleEqual((), retired_keys)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record1.updated, status.updated)

    def test_add_overwrites_expired(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 300
        t.store.set_expired((t.record1.key, ts))
        t.store.add(t.record1)

        expired_keys = tuple(t.store.get_expired())
        t.assertTupleEqual((), expired_keys)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record1.updated, status.updated)

    def test_add_overwrites_pending(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 300
        submitted = t.record1.updated + 500
        t.store.set_expired((t.record1.key, ts))
        t.store.set_pending((t.record1.key, submitted))
        t.store.add(t.record1)

        expired_keys = tuple(t.store.get_expired())
        t.assertTupleEqual((), expired_keys)

        pending_keys = tuple(t.store.get_pending())
        t.assertTupleEqual((), pending_keys)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record1.updated, status.updated)

    def test_add_overwrites_building(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 300
        started = t.record1.updated + 500
        t.store.set_expired((t.record1.key, ts))
        t.store.set_pending((t.record1.key, started - 100))
        t.store.set_building((t.record1.key, started))
        t.store.add(t.record1)

        expired_keys = tuple(t.store.get_expired())
        t.assertTupleEqual((), expired_keys)

        pending_keys = tuple(t.store.get_pending())
        t.assertTupleEqual((), pending_keys)

        building_keys = tuple(t.store.get_building())
        t.assertTupleEqual((), building_keys)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        key, status = result[0]
        t.assertEqual(t.record1.key, key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record1.updated, status.updated)


class DeviceMonitorChangeTest(_BaseTest):
    """
    Test when a device changes its monitor.
    """

    def test_add_monitor_change(t):
        t.store.add(t.record1)
        newmonitor = "b2"
        updated = t.record1.updated + 1000
        newrecord = ConfigRecord.make(
            t.record1.service,
            newmonitor,
            t.record1.device,
            t.record1.uid,
            updated,
            t.record1.config,
        )
        t.store.add(newrecord)

        result = t.store.get(t.record1.key)
        t.assertIsNone(result)

        result = t.store.get(newrecord.key)
        t.assertEqual(newrecord, result)


class DeviceUIDTest(TestCase):

    layer = RedisLayer

    def setUp(t):
        t.device_name = "qadevice"
        t.device_uid = "/zport/dmd/Devices/Server/Linux/devices/qadevice"
        t.store = ConfigStore(t.layer.redis)
        t.config1 = _make_config("qadevice", "qadevice", "abc-test-01")
        t.config2 = _make_config("qadevice", "qadevice", "abc-test-01")
        t.record1 = ConfigRecord.make(
            "snmp",
            "localhost",
            t.device_name,
            t.device_uid,
            123456.23,
            t.config1,
        )
        t.record2 = ConfigRecord.make(
            "ping",
            "localhost",
            t.device_name,
            t.device_uid,
            123654.23,
            t.config2,
        )

    def tearDown(t):
        del t.store
        del t.config1
        del t.config2
        del t.record1
        del t.record2

    def test_uid(t):
        t.store.add(t.record1)
        t.store.add(t.record2)

        t.assertEqual(t.device_uid, t.store.get_uid(t.device_name))

        records = tuple(
            t.store.get(key)
            for key in t.store.search(ConfigQuery(device=t.device_name))
        )

        t.assertEqual(2, len(records))
        t.assertNotEqual(records[0], records[1])
        t.assertEqual(records[0].uid, records[1].uid)
        t.assertEqual(t.device_uid, records[0].uid)

    def test_uid_after_one_removal(t):
        t.store.add(t.record1)
        t.store.add(t.record2)
        t.store.remove(t.record1.key)

        records = tuple(
            t.store.get(key)
            for key in t.store.search(ConfigQuery(device=t.device_name))
        )

        t.assertEqual(1, len(records))
        t.assertEqual(t.device_uid, records[0].uid)

    def test_uid_after_removing_all(t):
        t.store.add(t.record1)
        t.store.add(t.record2)
        t.store.remove(t.record1.key, t.record2.key)

        records = tuple(
            t.store.get(key)
            for key in t.store.search(ConfigQuery(device=t.device_name))
        )

        t.assertEqual(0, len(records))
        t.assertIsNone(t.store.get_uid(t.device_name))


def _make_config(_id, configId, guid):
    config = DeviceProxy()
    config.id = _id
    config._config_id = configId
    config._device_guid = guid
    return config


# _compare_configs used to monkeypatch DeviceProxy
# to make equivalent instances equal.


def _compare_configs(self, cfg):
    return all(
        (
            self.id == cfg.id,
            self._config_id == cfg._config_id,
            self._device_guid == cfg._device_guid,
        )
    )
