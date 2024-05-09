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

from ..cache import CacheKey, CacheQuery, CacheRecord, ConfigStatus
from ..cache.storage import ConfigStore


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
        key = CacheKey("a", "b", "c")
        t.assertIsNone(t.store.get(key))

    def test_get_with_nondefault_default(t):
        key = CacheKey("a", "b", "c")
        dflt = object()
        t.assertEqual(t.store.get(key, dflt), dflt)

    def test_remove(t):
        t.assertIsNone(t.store.remove())

    def test_get_status_no_keys(t):
        result = t.store.get_status()
        t.assertIsInstance(result, collections.Iterable)
        t.assertTupleEqual(tuple(result), ())

    def test_get_status_unknown_key(t):
        key = CacheKey("a", "b", "c")
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


class NoConfigTest(TestCase):
    """Test statuses when no config is present."""

    layer = RedisLayer

    key = CacheKey("a", "b", "c")
    now = 12345.0

    def setUp(t):
        t.store = ConfigStore(t.layer.redis)

    def tearDown(t):
        del t.store

    def test_current_status(t):
        t.assertIsNone(next(t.store.get_status(t.key), None))

    def test_search_with_status(t):
        t.store.set_pending((t.key, t.now))
        t.assertEqual(0, len(tuple(t.store.search())))

    def test_retired(t):
        expected = ConfigStatus.Retired(t.key, None, t.now)
        t.store.set_retired((t.key, t.now))
        status = next(t.store.get_status(t.key), None)
        t.assertEqual(expected, status)

    def test_expired(t):
        expected = ConfigStatus.Expired(t.key, None, t.now)
        t.store.set_expired((t.key, t.now))
        status = next(t.store.get_status(t.key), None)
        t.assertEqual(expected, status)

    def test_pending(t):
        expected = ConfigStatus.Pending(t.key, None, t.now)
        t.store.set_pending((t.key, t.now))
        status = next(t.store.get_status(t.key), None)
        t.assertEqual(expected, status)

    def test_building(t):
        expected = ConfigStatus.Building(t.key, None, t.now)
        t.store.set_building((t.key, t.now))
        status = next(t.store.get_status(t.key), None)
        t.assertEqual(expected, status)


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
        t.record1 = CacheRecord.make(
            t.fields[0].service,
            t.fields[0].monitor,
            t.fields[0].device,
            t.fields[0].uid,
            t.fields[0].updated,
            t.config1,
        )
        t.record2 = CacheRecord.make(
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
        expected1 = CacheKey(
            t.fields[0].service,
            t.fields[0].monitor,
            t.fields[0].device,
        )
        expected2 = CacheKey(
            t.fields[1].service,
            t.fields[1].monitor,
            t.fields[1].device,
        )
        result = tuple(t.store.search())
        t.assertEqual(2, len(result))
        t.assertIn(expected1, result)
        t.assertIn(expected2, result)

        result = t.store.get(t.record1.key)
        t.assertIsInstance(result, CacheRecord)
        t.assertEqual(t.record1, result)

        result = t.store.get(t.record2.key)
        t.assertIsInstance(result, CacheRecord)
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
                result = tuple(t.store.search(CacheQuery(**case)))
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
                result = tuple(t.store.search(CacheQuery(**case)))
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
                result = tuple(t.store.search(CacheQuery(**args)))
                t.assertEqual(count, len(result))


class ConfigStoreGetStatusTest(_BaseTest):
    """Test the `get_status` method of ConfigStore."""

    def test_get_status(t):
        t.store.add(t.record1)
        t.store.add(t.record2)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        status = result[0]
        t.assertEqual(t.record1.key, status.key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.fields[0].updated, status.updated)

        result = tuple(t.store.get_status(t.record2.key))
        t.assertEqual(1, len(result))
        status = result[0]
        t.assertEqual(t.record2.key, status.key)
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
        t.assertEqual(1, len(result))
        status = result[0]
        t.assertEqual(t.record1.key, status.key)
        t.assertEqual(t.record1.updated, status.updated)

    def test_get_older_equal_single(t):
        t.store.add(t.record1)
        result = tuple(t.store.get_older(t.record1.updated))
        t.assertEqual(1, len(result))
        status = result[0]
        t.assertEqual(t.record1.key, status.key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record1.updated, status.updated)

    def test_get_older_equal_multiple(t):
        t.store.add(t.record1)
        t.store.add(t.record2)

        result = tuple(t.store.get_older(t.record1.updated))
        t.assertEqual(1, len(result))
        status = result[0]
        t.assertEqual(t.record1.key, status.key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record1.updated, status.updated)

        result = sorted(
            t.store.get_older(t.record2.updated), key=lambda x: x.updated
        )
        t.assertEqual(2, len(result))
        status = result[0]
        t.assertEqual(t.record1.key, status.key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record1.updated, status.updated)

        status = result[1]
        t.assertEqual(t.record2.key, status.key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record2.updated, status.updated)

    def test_get_older_greater_single(t):
        t.store.add(t.record1)
        result = tuple(t.store.get_older(t.record1.updated + 1))
        t.assertEqual(1, len(result))
        status = result[0]
        t.assertEqual(t.record1.key, status.key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record1.updated, status.updated)

    def test_get_older_greater_multiple(t):
        t.store.add(t.record1)
        t.store.add(t.record2)

        result = tuple(t.store.get_older(t.record1.updated + 1))
        t.assertEqual(1, len(result))
        status = result[0]
        t.assertEqual(t.record1.key, status.key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record1.updated, status.updated)

        result = sorted(
            t.store.get_older(t.record2.updated + 1), key=lambda x: x.updated
        )
        t.assertEqual(2, len(result))
        status = result[0]
        t.assertEqual(t.record1.key, status.key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record1.updated, status.updated)

        status = result[1]
        t.assertEqual(t.record2.key, status.key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record2.updated, status.updated)


class ConfigStoreGetNewerTest(_BaseTest):
    """Test the `get_newer` method of ConfigStore."""

    def test_get_newer_less_single(t):
        t.store.add(t.record1)
        result = tuple(t.store.get_newer(t.record1.updated - 1))
        t.assertEqual(1, len(result))
        status = result[0]
        t.assertEqual(t.record1.key, status.key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record1.updated, status.updated)

    def test_get_newer_less_multiple(t):
        t.store.add(t.record1)
        t.store.add(t.record2)

        result = sorted(
            t.store.get_newer(t.record1.updated - 1), key=lambda x: x.updated
        )
        t.assertEqual(2, len(result))
        status = result[0]
        t.assertEqual(t.record1.key, status.key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record1.updated, status.updated)
        status = result[1]
        t.assertEqual(t.record2.key, status.key)
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
        status = result[0]
        t.assertEqual(t.record2.key, status.key)
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
        status = result[0]
        t.assertEqual(t.record2.key, status.key)
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(t.record2.updated, status.updated)


class SetStatusOnceTest(_BaseTest):
    """
    Test the behavior when a set_<status> method is called once.
    """

    def test_retired_once(t):
        ts = t.record1.updated + 100
        expected = ConfigStatus.Retired(t.record1.key, None, ts)
        t.store.set_retired((t.record1.key, ts))

        actual = next(t.store.get_retired(), None)
        t.assertEqual(expected, actual)
        actual = next(t.store.get_status(t.record1.key), None)
        t.assertEqual(expected, actual)

        actual = next(t.store.get_expired(), None)
        t.assertIsNone(actual)
        actual = next(t.store.get_pending(), None)
        t.assertIsNone(actual)
        actual = next(t.store.get_building(), None)
        t.assertIsNone(actual)

    def test_expired_once(t):
        ts = t.record1.updated + 100
        expected = ConfigStatus.Expired(t.record1.key, None, ts)
        t.store.set_expired((t.record1.key, ts))

        actual = next(t.store.get_expired(), None)
        t.assertEqual(expected, actual)
        actual = next(t.store.get_status(t.record1.key), None)
        t.assertEqual(expected, actual)

        actual = next(t.store.get_retired(), None)
        t.assertIsNone(actual)
        actual = next(t.store.get_pending(), None)
        t.assertIsNone(actual)
        actual = next(t.store.get_building(), None)
        t.assertIsNone(actual)

    def test_pending_once(t):
        ts = t.record1.updated + 100
        expected = ConfigStatus.Pending(t.record1.key, None, ts)
        t.store.set_pending((t.record1.key, ts))

        actual = next(t.store.get_pending(), None)
        t.assertEqual(expected, actual)
        actual = next(t.store.get_status(t.record1.key), None)
        t.assertEqual(expected, actual)

        actual = next(t.store.get_retired(), None)
        t.assertIsNone(actual)
        actual = next(t.store.get_expired(), None)
        t.assertIsNone(actual)
        actual = next(t.store.get_building(), None)
        t.assertIsNone(actual)

    def test_building_once(t):
        ts = t.record1.updated + 100
        expected = ConfigStatus.Building(t.record1.key, None, ts)
        t.store.set_building((t.record1.key, ts))

        actual = next(t.store.get_building(), None)
        t.assertEqual(expected, actual)
        actual = next(t.store.get_status(t.record1.key), None)
        t.assertEqual(expected, actual)

        actual = next(t.store.get_retired(), None)
        t.assertIsNone(actual)
        actual = next(t.store.get_expired(), None)
        t.assertIsNone(actual)
        actual = next(t.store.get_pending(), None)
        t.assertIsNone(actual)


class SetStatusTwiceTest(_BaseTest):
    """
    Test the behavior when a set_<status> method is called twice
    with different timestamp values.
    """

    def test_retired_twice(t):
        ts1 = t.record1.updated + 100
        ts2 = t.record1.updated + 200
        expected = ConfigStatus.Retired(t.record1.key, None, ts2)
        t.store.set_retired((t.record1.key, ts1))
        t.store.set_retired((t.record1.key, ts2))

        actual = next(t.store.get_retired(), None)
        t.assertEqual(expected, actual)
        actual = next(t.store.get_status(t.record1.key), None)
        t.assertEqual(expected, actual)

        actual = next(t.store.get_expired(), None)
        t.assertIsNone(actual)
        actual = next(t.store.get_pending(), None)
        t.assertIsNone(actual)
        actual = next(t.store.get_building(), None)
        t.assertIsNone(actual)

    def test_expired_twice(t):
        ts1 = t.record1.updated + 100
        ts2 = t.record1.updated + 200
        expected = ConfigStatus.Expired(t.record1.key, None, ts2)
        t.store.set_expired((t.record1.key, ts1))
        t.store.set_expired((t.record1.key, ts2))

        actual = next(t.store.get_expired(), None)
        t.assertEqual(expected, actual)
        actual = next(t.store.get_status(t.record1.key), None)
        t.assertEqual(expected, actual)

        actual = next(t.store.get_retired(), None)
        t.assertIsNone(actual)
        actual = next(t.store.get_pending(), None)
        t.assertIsNone(actual)
        actual = next(t.store.get_building(), None)
        t.assertIsNone(actual)

    def test_pending_twice(t):
        ts1 = t.record1.updated + 100
        ts2 = t.record1.updated + 200
        expected = ConfigStatus.Pending(t.record1.key, None, ts2)
        t.store.set_pending((t.record1.key, ts1))
        t.store.set_pending((t.record1.key, ts2))

        actual = next(t.store.get_pending(), None)
        t.assertEqual(expected, actual)
        actual = next(t.store.get_status(t.record1.key), None)
        t.assertEqual(expected, actual)

        actual = next(t.store.get_retired(), None)
        t.assertIsNone(actual)
        actual = next(t.store.get_expired(), None)
        t.assertIsNone(actual)
        actual = next(t.store.get_building(), None)
        t.assertIsNone(actual)

    def test_building_twice(t):
        ts1 = t.record1.updated + 100
        ts2 = t.record1.updated + 200
        expected = ConfigStatus.Building(t.record1.key, None, ts2)
        t.store.set_building((t.record1.key, ts1))
        t.store.set_building((t.record1.key, ts2))

        actual = next(t.store.get_building(), None)
        t.assertEqual(expected, actual)
        actual = next(t.store.get_status(t.record1.key), None)
        t.assertEqual(expected, actual)

        actual = next(t.store.get_retired(), None)
        t.assertIsNone(actual)
        actual = next(t.store.get_expired(), None)
        t.assertIsNone(actual)
        actual = next(t.store.get_pending(), None)
        t.assertIsNone(actual)


class TestCurrentOnlyMethods(_BaseTest):
    """
    Verify that the get_older and get_newer methods work for Current status.
    """

    def test_older_with_current(t):
        t.store.add(t.record1)

        status = next(t.store.get_status(t.record1.key), None)
        t.assertIsInstance(status, ConfigStatus.Current)

        older = next(t.store.get_older(t.record1.updated), None)
        t.assertEqual(status, older)

    def test_older_with_retired(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 500
        t.store.set_retired((t.record1.key, ts))

        status = next(t.store.get_status(t.record1.key), None)
        t.assertIsInstance(status, ConfigStatus.Retired)

        older = next(t.store.get_older(t.record1.updated), None)
        t.assertIsNone(older)

    def test_older_with_expired(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 500
        t.store.set_expired((t.record1.key, ts))

        status = next(t.store.get_status(t.record1.key), None)
        t.assertIsInstance(status, ConfigStatus.Expired)

        older = next(t.store.get_older(t.record1.updated), None)
        t.assertIsNone(older)

    def test_older_with_pending(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 500
        t.store.set_pending((t.record1.key, ts))

        status = next(t.store.get_status(t.record1.key), None)
        t.assertIsInstance(status, ConfigStatus.Pending)

        older = next(t.store.get_older(t.record1.updated), None)
        t.assertIsNone(older)

    def test_older_with_building(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 500
        t.store.set_building((t.record1.key, ts))

        status = next(t.store.get_status(t.record1.key), None)
        t.assertIsInstance(status, ConfigStatus.Building)

        older = next(t.store.get_older(t.record1.updated), None)
        t.assertIsNone(older)

    def test_newer_with_current(t):
        t.store.add(t.record1)

        status = next(t.store.get_status(t.record1.key), None)
        t.assertIsInstance(status, ConfigStatus.Current)

        newer = next(t.store.get_newer(t.record1.updated - 1), None)
        t.assertEqual(status, newer)

    def test_newer_with_retired(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 500
        t.store.set_retired((t.record1.key, ts))

        status = next(t.store.get_status(t.record1.key), None)
        t.assertIsInstance(status, ConfigStatus.Retired)

        newer = next(t.store.get_newer(t.record1.updated - 1), None)
        t.assertIsNone(newer)

    def test_newer_with_expired(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 500
        t.store.set_expired((t.record1.key, ts))

        status = next(t.store.get_status(t.record1.key), None)
        t.assertIsInstance(status, ConfigStatus.Expired)

        newer = next(t.store.get_newer(t.record1.updated - 1), None)
        t.assertIsNone(newer)

    def test_newer_with_pending(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 500
        t.store.set_pending((t.record1.key, ts))

        status = next(t.store.get_status(t.record1.key), None)
        t.assertIsInstance(status, ConfigStatus.Pending)

        newer = next(t.store.get_newer(t.record1.updated - 1), None)
        t.assertIsNone(newer)

    def test_newer_with_building(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 500
        t.store.set_building((t.record1.key, ts))

        status = next(t.store.get_status(t.record1.key), None)
        t.assertIsInstance(status, ConfigStatus.Building)

        newer = next(t.store.get_newer(t.record1.updated - 1), None)
        t.assertIsNone(newer)


class GetStatusTest(_BaseTest):
    """
    Verify that get_status returns all the statuses.
    """

    def test_current(t):
        t.store.add(t.record1)
        expected = ConfigStatus.Current(
            t.record1.key, t.record1.uid, t.record1.updated
        )
        actual = next(t.store.get_status(t.record1.key), None)
        t.assertEqual(expected, actual)

    def test_retired(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 100
        t.store.set_retired((t.record1.key, ts))
        expected = ConfigStatus.Retired(t.record1.key, t.record1.uid, ts)
        actual = next(t.store.get_status(t.record1.key), None)
        t.assertEqual(expected, actual)

    def test_expired(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 200
        t.store.set_expired((t.record1.key, ts))
        expected = ConfigStatus.Expired(t.record1.key, t.record1.uid, ts)
        actual = next(t.store.get_status(t.record1.key), None)
        t.assertEqual(expected, actual)

    def test_pending(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 300
        t.store.set_pending((t.record1.key, ts))
        expected = ConfigStatus.Pending(t.record1.key, t.record1.uid, ts)
        actual = next(t.store.get_status(t.record1.key), None)
        t.assertEqual(expected, actual)

    def test_building(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 400
        t.store.set_building((t.record1.key, ts))
        expected = ConfigStatus.Building(t.record1.key, t.record1.uid, ts)
        actual = next(t.store.get_status(t.record1.key), None)
        t.assertEqual(expected, actual)


class TestClearStatus(_BaseTest):
    """
    Test clearing the status.
    """

    def test_clear_from_current(t):
        t.store.add(t.record1)
        t.store.clear_status(t.record1.key)

        status = next(t.store.get_status(t.record1.key), None)
        t.assertIsInstance(status, ConfigStatus.Current)

        t.assertIsNone(next(t.store.get_retired(), None))
        t.assertIsNone(next(t.store.get_expired(), None))
        t.assertIsNone(next(t.store.get_pending(), None))
        t.assertIsNone(next(t.store.get_building(), None))

    def test_clear_from_expired_to_current(t):
        t.store.add(t.record1)
        ts = t.record1.updated + 100
        t.store.set_expired((t.record1.key, ts))

        t.store.clear_status(t.record1.key)

        status = next(t.store.get_status(t.record1.key), None)
        t.assertIsInstance(status, ConfigStatus.Current)

        t.assertIsNone(next(t.store.get_retired(), None))
        t.assertIsNone(next(t.store.get_expired(), None))
        t.assertIsNone(next(t.store.get_pending(), None))
        t.assertIsNone(next(t.store.get_building(), None))

    def test_clear_from_retired(t):
        retired = t.record1.updated + 100
        t.store.set_retired((t.record1.key, retired))

        t.store.clear_status(t.record1.key)

        t.assertIsNone(next(t.store.get_status(t.record1.key), None))
        t.assertIsNone(next(t.store.get_retired(), None))
        t.assertIsNone(next(t.store.get_expired(), None))
        t.assertIsNone(next(t.store.get_pending(), None))
        t.assertIsNone(next(t.store.get_building(), None))

    def test_clear_from_expired(t):
        ts = t.record1.updated + 100
        t.store.set_expired((t.record1.key, ts))

        t.store.clear_status(t.record1.key)

        t.assertIsNone(next(t.store.get_status(t.record1.key), None))
        t.assertIsNone(next(t.store.get_retired(), None))
        t.assertIsNone(next(t.store.get_expired(), None))
        t.assertIsNone(next(t.store.get_pending(), None))
        t.assertIsNone(next(t.store.get_building(), None))

    def test_clear_from_pending(t):
        ts = t.record1.updated + 100
        t.store.set_pending((t.record1.key, ts))

        t.store.clear_status(t.record1.key)

        t.assertIsNone(next(t.store.get_status(t.record1.key), None))
        t.assertIsNone(next(t.store.get_retired(), None))
        t.assertIsNone(next(t.store.get_expired(), None))
        t.assertIsNone(next(t.store.get_pending(), None))
        t.assertIsNone(next(t.store.get_building(), None))

    def test_clear_from_building(t):
        ts = t.record1.updated + 100
        t.store.set_building((t.record1.key, ts))

        t.store.clear_status(t.record1.key)

        t.assertIsNone(next(t.store.get_status(t.record1.key), None))
        t.assertIsNone(next(t.store.get_retired(), None))
        t.assertIsNone(next(t.store.get_expired(), None))
        t.assertIsNone(next(t.store.get_pending(), None))
        t.assertIsNone(next(t.store.get_building(), None))


class TestStatusChangesFromRetired(_BaseTest):
    """
    Test changing the status of a config.
    """

    def test_retired_to_expired(t):
        retired = t.record1.updated + 100
        t.store.set_retired((t.record1.key, retired))

        expired = t.record1.updated + 300
        t.store.set_expired((t.record1.key, expired))

        actual = next(t.store.get_retired(), None)
        t.assertIsNone(actual)

        expected = ConfigStatus.Expired(t.record1.key, None, expired)
        actual = next(t.store.get_expired(), None)
        t.assertEqual(expected, actual)

    def test_retired_to_pending(t):
        retired = t.record1.updated + 100
        t.store.set_retired((t.record1.key, retired))

        pending = t.record1.updated + 300
        t.store.set_pending((t.record1.key, pending))

        actual = next(t.store.get_retired(), None)
        t.assertIsNone(actual)

        expected = ConfigStatus.Pending(t.record1.key, None, pending)
        actual = next(t.store.get_pending(), None)
        t.assertEqual(expected, actual)

    def test_retired_to_building(t):
        retired = t.record1.updated + 100
        t.store.set_retired((t.record1.key, retired))

        building = t.record1.updated + 300
        t.store.set_building((t.record1.key, building))

        actual = next(t.store.get_retired(), None)
        t.assertIsNone(actual)

        expected = ConfigStatus.Building(t.record1.key, None, building)
        actual = next(t.store.get_building(), None)
        t.assertEqual(expected, actual)


class TestStatusChangesFromExpired(_BaseTest):
    """
    Test changing the status of a config.
    """

    def test_expired_to_retired(t):
        expired = t.record1.updated + 100
        t.store.set_expired((t.record1.key, expired))

        retired = t.record1.updated + 300
        t.store.set_retired((t.record1.key, retired))

        actual = next(t.store.get_expired(), None)
        t.assertIsNone(actual)

        expected = ConfigStatus.Retired(t.record1.key, None, retired)
        actual = next(t.store.get_retired(), None)
        t.assertEqual(expected, actual)

    def test_expired_to_pending(t):
        expired = t.record1.updated + 100
        t.store.set_expired((t.record1.key, expired))

        pending = t.record1.updated + 300
        t.store.set_pending((t.record1.key, pending))

        actual = next(t.store.get_expired(), None)
        t.assertIsNone(actual)

        expected = ConfigStatus.Pending(t.record1.key, None, pending)
        actual = next(t.store.get_pending(), None)
        t.assertEqual(expected, actual)

    def test_expired_to_building(t):
        expired = t.record1.updated + 100
        t.store.set_expired((t.record1.key, expired))

        building = t.record1.updated + 300
        t.store.set_building((t.record1.key, building))

        actual = next(t.store.get_expired(), None)
        t.assertIsNone(actual)

        expected = ConfigStatus.Building(t.record1.key, None, building)
        actual = next(t.store.get_building(), None)
        t.assertEqual(expected, actual)


class TestStatusChangesFromPending(_BaseTest):
    """
    Test changing the status of a config.
    """

    def test_pending_to_retired(t):
        pending = t.record1.updated + 100
        t.store.set_pending((t.record1.key, pending))

        retired = t.record1.updated + 300
        t.store.set_retired((t.record1.key, retired))

        actual = next(t.store.get_pending(), None)
        t.assertIsNone(actual)

        expected = ConfigStatus.Retired(t.record1.key, None, retired)
        actual = next(t.store.get_retired(), None)
        t.assertEqual(expected, actual)

    def test_pending_to_expired(t):
        pending = t.record1.updated + 100
        t.store.set_pending((t.record1.key, pending))

        expired = t.record1.updated + 300
        t.store.set_expired((t.record1.key, expired))

        actual = next(t.store.get_pending(), None)
        t.assertIsNone(actual)

        expected = ConfigStatus.Expired(t.record1.key, None, expired)
        actual = next(t.store.get_expired(), None)
        t.assertEqual(expected, actual)

    def test_pending_to_building(t):
        pending = t.record1.updated + 100
        t.store.set_pending((t.record1.key, pending))

        building = t.record1.updated + 300
        t.store.set_building((t.record1.key, building))

        actual = next(t.store.get_pending(), None)
        t.assertIsNone(actual)

        expected = ConfigStatus.Building(t.record1.key, None, building)
        actual = next(t.store.get_building(), None)
        t.assertEqual(expected, actual)


class TestStatusChangesFromBuilding(_BaseTest):
    """
    Test changing the status of a config.
    """

    def test_building_to_retired(t):
        building = t.record1.updated + 100
        t.store.set_building((t.record1.key, building))

        retired = t.record1.updated + 300
        t.store.set_retired((t.record1.key, retired))

        actual = next(t.store.get_building(), None)
        t.assertIsNone(actual)

        expected = ConfigStatus.Retired(t.record1.key, None, retired)
        actual = next(t.store.get_retired(), None)
        t.assertEqual(expected, actual)

    def test_building_to_expired(t):
        building = t.record1.updated + 100
        t.store.set_building((t.record1.key, building))

        expired = t.record1.updated + 300
        t.store.set_expired((t.record1.key, expired))

        actual = next(t.store.get_building(), None)
        t.assertIsNone(actual)

        expected = ConfigStatus.Expired(t.record1.key, None, expired)
        actual = next(t.store.get_expired(), None)
        t.assertEqual(expected, actual)

    def test_building_to_pending(t):
        building = t.record1.updated + 100
        t.store.set_building((t.record1.key, building))

        pending = t.record1.updated + 300
        t.store.set_pending((t.record1.key, pending))

        actual = next(t.store.get_building(), None)
        t.assertIsNone(actual)

        expected = ConfigStatus.Pending(t.record1.key, None, pending)
        actual = next(t.store.get_pending(), None)
        t.assertEqual(expected, actual)


class TestAddTransitions(_BaseTest):
    """
    Test status changes after adding a config.
    """

    def test_add_overwrites_retired(t):
        t.store.add(t.record1)
        retired = t.record1.updated + 100
        t.store.set_retired((t.record1.key, retired))
        t.store.add(t.record1)

        retired_keys = tuple(t.store.get_retired())
        t.assertTupleEqual((), retired_keys)

        result = tuple(t.store.get_status(t.record1.key))
        t.assertEqual(1, len(result))
        status = result[0]
        t.assertEqual(t.record1.key, status.key)
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
        status = result[0]
        t.assertEqual(t.record1.key, status.key)
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
        status = result[0]
        t.assertEqual(t.record1.key, status.key)
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
        status = result[0]
        t.assertEqual(t.record1.key, status.key)
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
        newrecord = CacheRecord.make(
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
        t.record1 = CacheRecord.make(
            "snmp",
            "localhost",
            t.device_name,
            t.device_uid,
            123456.23,
            t.config1,
        )
        t.record2 = CacheRecord.make(
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
            for key in t.store.search(CacheQuery(device=t.device_name))
        )

        t.assertEqual(2, len(records))
        t.assertNotEqual(records[0], records[1])
        t.assertEqual(records[0].uid, records[1].uid)
        t.assertEqual(t.device_uid, records[0].uid)

    def test_uid_after_one_removal(t):
        t.store.add(t.record1)
        t.store.add(t.record2)
        t.store.remove(t.record1.key)

        actual = t.store.get_uid(t.device_name)
        t.assertEqual(t.device_uid, actual)

        records = tuple(
            t.store.get(key)
            for key in t.store.search(CacheQuery(device=t.device_name))
        )
        t.assertEqual(1, len(records))
        t.assertEqual(t.device_uid, records[0].uid)

    def test_uid_after_removing_all(t):
        t.store.add(t.record1)
        t.store.add(t.record2)
        t.store.remove(t.record1.key, t.record2.key)

        records = tuple(
            t.store.get(key)
            for key in t.store.search(CacheQuery(device=t.device_name))
        )
        t.assertEqual(0, len(records))
        t.assertIsNone(t.store.get_uid(t.device_name))


def _make_config(_id, configId, guid):
    config = DeviceProxy()
    config.id = _id
    config._config_id = configId
    config._device_guid = guid
    config.data = u"fancy"
    return config


def _compare_configs(self, cfg):
    # _compare_configs used to monkeypatch DeviceProxy
    # to make equivalent instances equal.
    return all(
        (
            self.id == cfg.id,
            self._config_id == cfg._config_id,
            self._device_guid == cfg._device_guid,
        )
    )
