##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import collections
import re
import time

from unittest import TestCase

from twisted.spread.jelly import jelly, unjelly

from Products.ZenCollector.services.config import DeviceProxy
from Products.Jobber.tests.utils import RedisLayer

from ..configstore import DeviceConfigurationStore, _basetemplate

# from .utils import subTest, RedisLayer

_serviceid = "Products.ZenHub.services.SnmpPerformanceConfig"
_keytemplate = _basetemplate.format(_serviceid)


class EmptyDeviceConfigurationStoreTest(TestCase):
    """Test an empty DeviceConfigurationStore object."""

    layer = RedisLayer

    def setUp(t):
        t.store = DeviceConfigurationStore(t.layer.redis, _serviceid)

    def tearDown(t):
        t.layer.redis.flushall()

    def test_keys(t):
        t.assertIsInstance(t.store.keys(), collections.Iterable)
        t.assertTupleEqual(tuple(t.store.keys()), ())

    def test_values(t):
        t.assertIsInstance(t.store.values(), collections.Iterable)
        t.assertTupleEqual(tuple(t.store.values()), ())

    def test_items(t):
        t.assertIsInstance(t.store.items(), collections.Iterable)
        t.assertTupleEqual(tuple(t.store.items()), ())

    def test___iter__(t):
        t.assertIsInstance(iter(t.store), collections.Iterable)
        t.assertTupleEqual(tuple(iter(t.store)), ())

    def test_mget(t):
        jobid = "123"
        actual = t.store.mget(jobid)
        t.assertIsInstance(actual, collections.Iterable)
        t.assertTupleEqual(tuple(actual), ())

    def test_mget_multiple(t):
        jobids = ("123", "456")
        actual = t.store.mget(*jobids)
        t.assertIsInstance(actual, collections.Iterable)
        t.assertTupleEqual(tuple(actual), ())

    def test_get(t):
        result = t.store.get("123")
        t.assertIsNone(result)

    def test_get_customdefault(t):
        expected = object()
        actual = t.store.get("123", default=expected)
        t.assertEqual(expected, actual)

    def test___getitem__(t):
        with t.assertRaises(KeyError):
            t.store["123"]

    def test_mdelete(t):
        t.store.mdelete("123")

    def test___del__(t):
        with t.assertRaises(KeyError):
            del t.store["123"]

    def test___len__(t):
        t.assertEqual(len(t.store), 0)

    def test___contains__(t):
        t.assertNotIn("123", t.store)

    # def test_search(t):
    #     searches = (
    #         {"status": "PENDING"},
    #         {"status": "PENDING", "userid": "celeste"},
    #         {"name": "Blooper", "created": 1551804881.024517},
    #         {"name": "Blooper", "userid": ("celeste", "mark")},
    #         {"description": re.compile("something")},
    #     )
    #     for params in searches:
    #         result = t.store.search(**params)
    #         t.assertIsInstance(result, collections.Iterable)
    #         jobids = tuple(result)
    #         t.assertEqual(len(jobids), 0)


def _makeDeviceProxy(**data):
    dp = DeviceProxy()
    dp.id = "mydev"
    dp._device_guid = "6a08f9fe-263d-11ee-87f3-0242ac110010"
    for k, v in data.items():
        setattr(dp, k, v)
    return _keytemplate.format(dp.configId), dp


class MutateDeviceConfigurationStoreTest(TestCase):
    """Test adding and altering a DeviceConfigurationStore's contents."""

    layer = RedisLayer

    def setUp(t):
        t.key, t.dp = _makeDeviceProxy()
        t.store = DeviceConfigurationStore(t.layer.redis, _serviceid)
        t.store[t.dp.configId] = t.dp

    def tearDown(t):
        t.layer.redis.flushall()
        del t.dp
        del t.key
        del t.store

    def test___setitem__(t):
        expected = str(jelly(t.dp))
        actual = t.layer.redis.get(t.key)
        t.assertEqual(expected, actual)

    def test___getitem__(t):
        actual = t.store[t.dp.configId]
        t.assertDictEqual(t.dp.__dict__, actual.__dict__)

    def test___len__(t):
        t.assertEqual(1, len(t.store))

    def test___contains__(t):
        t.assertTrue(t.dp.configId in t.store)

    def test_not__contains__(t):
        t.assertFalse("blah" in t.store)

    def test_keys(t):
        expected = (t.dp.configId,)
        actual = tuple(t.store.keys())
        t.assertTupleEqual(expected, actual)

    def test_values(t):
        expected = (t.dp.__dict__,)
        actual = (tuple(t.store.values())[0].__dict__,)
        t.assertTupleEqual(expected, actual)

    def test_items(t):
        expected = (t.dp.configId, t.dp.__dict__)
        data = tuple(t.store.items())[0]
        actual = (data[0], data[1].__dict__)
        t.assertTupleEqual(expected, actual)


# class ExpireKeysTest(TestCase):
#     """Test key expiration in JobStorage."""
#
#     layer = RedisLayer
#
#     initial = {
#         "jobid": "123",
#         "name": "TestJob",
#         "summary": "Products.Jobber.jobs.TestJob",
#         "description": "A test job",
#         "userid": "zenoss",
#         "logfile": "/opt/zenoss/log/jobs/123.log",
#         "created": 1551804881.024517,
#         "status": "PENDING",
#     }
#
#     expires = 10  # seconds
#
#     def setUp(t):
#         t.store = DeviceConfigurationStore(t.layer.redis, expires=t.expires)
#         t.jobid = t.initial["jobid"]
#         t.store[t.jobid] = t.initial
#
#     def tearDown(t):
#         t.layer.redis.flushall()
#
#     def test_ttl_initial(t):
#         ttl = t.store.ttl(t.jobid)
#         t.assertIsNone(ttl)
#
#     def test_ttl_for_received(t):
#         t.store.update(t.jobid, status="RECEIVED")
#         ttl = t.store.ttl(t.jobid)
#         t.assertIsNone(ttl)
#
#     def test_ttl_for_started(t):
#         t.store.update(t.jobid, status="STARTED")
#         ttl = t.store.ttl(t.jobid)
#         t.assertIsNone(ttl)
#
#     def test_ttl_for_retry(t):
#         t.store.update(t.jobid, status="RETRY")
#         ttl = t.store.ttl(t.jobid)
#         t.assertIsNone(ttl)
#
#     def test_ttl_for_revoked(t):
#         t.store.update(t.jobid, status="REVOKED")
#         time.sleep(1.0)
#         ttl = t.store.ttl(t.jobid)
#         t.assertIsNotNone(ttl)
#         t.assertLess(ttl, t.expires)
#
#     def test_ttl_for_success(t):
#         t.store.update(t.jobid, status="SUCCESS")
#         time.sleep(1.0)
#         ttl = t.store.ttl(t.jobid)
#         t.assertIsNotNone(ttl)
#         t.assertLess(ttl, t.expires)
#
#     def test_ttl_for_failure(t):
#         t.store.update(t.jobid, status="FAILURE")
#         time.sleep(1.0)
#         ttl = t.store.ttl(t.jobid)
#         t.assertIsNotNone(ttl)
#         t.assertLess(ttl, t.expires)
#
#     def test_ttl_for_aborted(t):
#         t.store.update(t.jobid, status="ABORTED")
#         time.sleep(1.0)
#         ttl = t.store.ttl(t.jobid)
#         t.assertIsNotNone(ttl)
#         t.assertLess(ttl, t.expires)
#
#
# def _buildData(jobnames, userids, base):
#     baseid = 100
#     basetm = 1551804881.024517
#     jobids = []
#     records = {}
#     combine = ((jn, uid) for jn in jobnames * 2 for uid in userids)
#     for n, (jobname, user) in enumerate(combine):
#         jobid = str(baseid + n)
#         jobids.append(jobid)
#         data = dict(base)
#         data.update(
#             {
#                 "jobid": jobid,
#                 "name": jobname,
#                 "userid": user,
#                 "created": basetm + n,
#                 "summary": data["summary"] % jobid,
#                 "description": data["description"] % user,
#                 "logfile": data["logfile"] % jobid,
#             }
#         )
#         records[jobid] = data
#     return jobids, records
#
#
# class PopulatedDeviceConfigurationStoreTest(TestCase):
#     """Test a populated DeviceConfigurationStore object."""
#
#     layer = RedisLayer
#
#     jobnames = ("FooJob", "BarJob", "BazJob")
#     userids = ("jill", "ed", "mary", "cal")
#     initial = {
#         "summary": "Products.Jobber.jobs.%s",
#         "description": "%s's test job",
#         "logfile": "/opt/zenoss/log/jobs/%s.log",
#         "status": "PENDING",
#     }
#     jobids, records = _buildData(jobnames, userids, initial)
#
#     def setUp(t):
#         t.store = DeviceConfigurationStore(t.layer.redis)
#         for jobid, data in t.records.items():
#             t.layer.redis.hmset("zenjobs:job:%s" % jobid, data)
#
#     def tearDown(t):
#         t.layer.redis.flushall()
#
#     def test_keys(t):
#         t.assertIsInstance(t.store.keys(), collections.Iterable)
#         expected = sorted(t.jobids)
#         actual = sorted(t.store.keys())
#         t.assertListEqual(expected, actual)
#
#     def test_values(t):
#         actual = t.store.values()
#         t.assertIsInstance(actual, collections.Iterable)
#         expected_jobids = list(t.jobids)
#         for actual_record in actual:
#             jobid = actual_record["jobid"]
#             with subTest(jobid=jobid):
#                 t.assertIn(jobid, expected_jobids)
#                 # remove now that jobid's been seen.
#                 expected_jobids.remove(jobid)
#                 expected_record = t.records[jobid]
#                 t.assertDictEqual(expected_record, actual_record)
#
#         t.assertListEqual(expected_jobids, [])
#
#     def test_items(t):
#         actual = t.store.items()
#         t.assertIsInstance(actual, collections.Iterable)
#         expected_jobids = list(t.jobids)
#         for jobid, actual_record in actual:
#             with subTest(jobid=jobid):
#                 t.assertIn(jobid, expected_jobids)
#                 # remove now that jobid's been seen.
#                 expected_jobids.remove(jobid)
#                 expected_record = t.records[jobid]
#                 t.assertDictEqual(expected_record, actual_record)
#
#         t.assertListEqual(expected_jobids, [])
#
#     def test___iter__(t):
#         t.assertIsInstance(iter(t.store), collections.Iterable)
#         expected = sorted(t.jobids)
#         actual = sorted(iter(t.store))
#         t.assertListEqual(expected, actual)
#
#     def test_getfield(t):
#         parameters = (
#             ("123", "created"),
#             ("112", "userid"),
#         )
#         for jobid, field in parameters:
#             with subTest(jobid=jobid, field=field):
#                 result = t.store.getfield(jobid, field)
#                 t.assertEqual(result, t.records[jobid][field])
#
#     def test_getfield_unset(t):
#         result = t.store.getfield("123", "started")
#         t.assertIsNone(result)
#
#     def test_getfield_customdefault(t):
#         default = object()
#         parameters = (
#             ("123", "created", t.records["123"]["created"]),
#             ("123", "started", default),
#         )
#         for jobid, field, expected in parameters:
#             with subTest(jobid=jobid, field=field, expected=expected):
#                 actual = t.store.getfield(jobid, field, default=default)
#                 t.assertEqual(expected, actual)
#
#     def test_getfield_wrongfield(t):
#         with t.assertRaises(AttributeError):
#             t.store.getfield("123", "foo")
#
#     def test_getfield_nonexistent_key(t):
#         result = t.store.getfield("2000", "name")
#         t.assertIsNone(result)
#
#     def test_update_badjob(t):
#         with t.assertRaises(KeyError):
#             t.store.update("1200", description="no such job")
#
#     def test_update_wrongfield(t):
#         with t.assertRaises(AttributeError):
#             t.store.update("105", foo="no such job or attribute")
#
#     def test_mget(t):
#         jobid = "123"
#         raw = t.store.mget(jobid)
#         t.assertIsInstance(raw, collections.Iterable)
#         actual = list(raw)
#         t.assertEqual(len(actual), 1)
#         actual_record = actual[0]
#         expected_record = t.records["123"]
#         t.assertDictEqual(expected_record, actual_record)
#
#     def test_mget_many(t):
#         parameters = (
#             (
#                 ("105", "112"),
#                 sorted((t.records["105"], t.records["112"])),
#             ),
#             (
#                 ("1005", "112"),
#                 [t.records["112"]],
#             ),
#             (
#                 ("102", "210"),
#                 [t.records["102"]],
#             ),
#             (
#                 ("180",),
#                 [],
#             ),
#             (
#                 ("1005", "1240"),
#                 [],
#             ),
#         )
#         for jobids, expected in parameters:
#             with subTest(jobids=jobids):
#                 result = t.store.mget(*jobids)
#                 t.assertIsInstance(result, collections.Iterable)
#                 t.assertListEqual(expected, sorted(result))
#
#     def test_get(t):
#         jobid = "120"
#         expected = t.records[jobid]
#         actual = t.store.get(jobid)
#         t.assertDictEqual(expected, actual)
#
#     def test_get_nonexistent(t):
#         actual = t.store.get("1200")
#         t.assertIsNone(actual)
#
#     def test_get_customdefault_exists(t):
#         default = object()
#         jobid = "120"
#         actual = t.store.get(jobid, default=default)
#         expected = t.records[jobid]
#         t.assertDictEqual(expected, actual)
#
#     def test_get_customdefault_nonexistent(t):
#         expected = object()
#         actual = t.store.get("1200", default=expected)
#         t.assertEqual(expected, actual)
#
#     def test___getitem__exists(t):
#         jobid = "108"
#         actual = t.store[jobid]
#         expected = t.records[jobid]
#         t.assertDictEqual(expected, actual)
#
#     def test___getitem__nonexistent(t):
#         with t.assertRaises(KeyError):
#             t.store["1200"]
#
#     def test_mdelete_exists(t):
#         jobid = "123"
#         t.store.mdelete(jobid)
#         t.assertFalse(t.layer.redis.exists("zenjobs:job:%s" % jobid))
#         t.assertIsNone(t.store.get(jobid))
#         remaining_jobids = set(t.store.keys())
#         missing_jobids = set(t.jobids) - remaining_jobids
#         t.assertSetEqual(missing_jobids, {jobid})
#
#     def test_mdelete_multiple(t):
#         jobs = ("110", "112", "115")
#         t.store.mdelete(*jobs)
#         for jobid in jobs:
#             with subTest(jobid=jobid):
#                 t.assertFalse(t.layer.redis.exists("zenjobs:job:%s" % jobid))
#                 t.assertIsNone(t.store.get(jobid))
#         remaining_jobids = set(t.store.keys())
#         missing_jobids = set(t.jobids) - remaining_jobids
#         t.assertSetEqual(missing_jobids, set(jobs))
#
#     def test___del__exists(t):
#         jobid = "118"
#         del t.store[jobid]
#         t.assertFalse(t.layer.redis.exists("zenjobs:job:%s" % jobid))
#         t.assertIsNone(t.store.get(jobid))
#         remaining_jobids = set(t.store.keys())
#         missing_jobids = set(t.jobids) - remaining_jobids
#         t.assertSetEqual(missing_jobids, {jobid})
#
#     def test___del__nonexistent(t):
#         with t.assertRaises(KeyError):
#             del t.store["1200"]
#
#     def test___len__(t):
#         t.assertEqual(len(t.store), len(t.jobids))
#
#     def test___contains__(t):
#         t.assertNotIn("1200", t.store)
#         t.assertIn("100", t.store)
#
#     def test___setitem__wrongfield(t):
#         with t.assertRaises(AttributeError):
#             t.store["123"] = {"jobid": "123", "foo": 10}
#
#     def test_searches(t):
#         parameters = (
#             (
#                 {"status": "PENDING"},
#                 sorted(t.jobids),
#             ),
#             (
#                 {"status": "PENDING", "userid": "jill"},
#                 ["100", "104", "108", "112", "116", "120"],
#             ),
#             (
#                 {"name": "FooJob", "created": 1551804881.024517},
#                 ["100"],
#             ),
#             (
#                 {"name": "BarJob", "userid": ("ed", "cal")},
#                 ["105", "107", "117", "119"],
#             ),
#             (
#                 {"description": re.compile("mary")},
#                 sorted(["114", "110", "118", "102", "106", "122"]),
#             ),
#         )
#         for query, expected in parameters:
#             with subTest(query=query):
#                 result = t.store.search(**query)
#                 t.assertIsInstance(result, collections.Iterable)
#                 actual = sorted(result)
#                 t.assertListEqual(expected, actual)
