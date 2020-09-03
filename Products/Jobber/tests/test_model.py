##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import itertools
import types

from celery import states
from mock import patch
from unittest import TestCase

from Products.Zuul import marshal
from Products.Zuul.interfaces import IMarshallable, IInfo
from zope.component import getGlobalSiteManager

from ..jobs import Job
from ..model import (
    build_redis_record,
    IJobRecord,
    IJobStore,
    JobRecord,
    JobRecordMarshaller,
    LegacySuport,
    update_job_status,
)
from ..storage import JobStore, Fields
from ..zenjobs import app
from .utils import subTest, RedisLayer

UNEXPECTED = type("UNEXPECTED", (object,), {})()
PATH = {"src": "Products.Jobber.model"}


class JobRecordTest(TestCase):
    """Test the JobRecord class."""

    def setUp(t):
        t.data = {
            "jobid": "123",
            "name": "Products.Jobber.jobs.FooJob",
            "summary": "FooJob",
            "description": "A foo job",
            "userid": "zenoss",
            "logfile": "/opt/zenoss/log/jobs/123.log",
            "created": 1551804881.024517,
            "started": 1551804891.863857,
            "finished": 1551805270.154359,
            "status": "SUCCESS",
            "details": {
                "foo": "foo string",
                "bar": 123,
                "baz": 34597945.00234,
            },
        }

    def test_interfaces(t):
        for intf in (IJobRecord, IMarshallable, IInfo):
            with subTest(interface=intf):
                t.assertTrue(intf.implementedBy(JobRecord))
                j = JobRecord.make({})
                t.assertTrue(intf.providedBy(j))

    def test_attributes(t):
        # Assert that JobRecord has all the attributes specified by Fields.
        j = JobRecord.make({})
        missing_names = set(Fields.viewkeys()) - set(dir(j))
        t.assertSetEqual(set(), missing_names)

    def test_has_methods(t):
        # Assert that the appropriate methods exist.
        methods = ("abort", "wait")
        for m in methods:
            with subTest(method=m):
                result = getattr(JobRecord, m, None)
                t.assertIsInstance(result, types.UnboundMethodType)

    def test_dir_keys(t):
        j = JobRecord.make(t.data)
        expected = t.data.keys()
        expected.remove("details")
        expected.extend(t.data["details"].keys())
        expected.extend((
            "details", "id", "make", "uid",
            "uuid", "duration", "complete", "abort", "wait", "result",
        ))
        expected = sorted(expected)
        actual = [a for a in dir(j) if not a.startswith("__")]
        t.assertListEqual(expected, actual)

    def test_details_are_exposed(t):
        j = JobRecord.make({})
        j.details = {"foo": 1}
        t.assertEqual(1, j.foo)
        t.assertIn("foo", dir(j))
        t.assertIn("foo", j.__dict__)
        t.assertEqual(1, j.__dict__["foo"])

    def test_details_are_not_writable(t):
        j = JobRecord.make({})
        j.details = {"foo": 1}
        with t.assertRaises(AttributeError):
            j.foo = 3

    def test_make_badfield(t):
        with t.assertRaises(AttributeError):
            JobRecord.make({"foo": 1})

    def test_uuid(t):
        job = JobRecord.make(t.data)
        t.assertEqual(job.jobid, job.uuid)

    def test_make(t):
        actual = JobRecord.make(t.data)
        expected = itertools.chain(
            t.data.items(),
            (
                ("complete", True),
                ("duration", t.data["finished"] - t.data["started"]),
            ),
        )
        for attribute, expected_value in expected:
            actual_value = getattr(actual, attribute, UNEXPECTED)
            with subTest(attribute=attribute):
                t.assertEqual(expected_value, actual_value)

    def test_complete(t):
        parameters = {
            ("PENDING", False),
            ("RETRY", False),
            ("RECEIVED", False),
            ("STARTED", False),
            ("REVOKED", True),
            ("ABORTED", True),
            ("FAILURE", True),
            ("SUCCESS", True),
        }
        record = JobRecord.make(t.data)
        for status, expected in parameters:
            with subTest(status=status):
                record.status = status
                t.assertEqual(
                    expected, record.complete, msg="status=%s" % status,
                )

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_duration(t, time):
        current_tm = 1551804885.298103
        completed_duration = t.data["finished"] - t.data["started"]
        incomplete_duration = current_tm - t.data["started"]
        time.time.return_value = current_tm
        parameters = {
            ("PENDING", None),
            ("RETRY", incomplete_duration),
            ("RECEIVED", None),
            ("STARTED", incomplete_duration),
            ("REVOKED", completed_duration),
            ("ABORTED", completed_duration),
            ("FAILURE", completed_duration),
            ("SUCCESS", completed_duration),
        }
        record = JobRecord.make(t.data)
        for status, expected in parameters:
            with subTest(status=status):
                record.status = status
                t.assertEqual(expected, record.duration)


class BaseBuildRedisRecord(object):

    def setUp(t):
        t.args = (10,)
        t.kw = {"named": "charger"}
        t.jobid = "12345"
        t.expected = {
            "logfile": "/opt/zenoss/log/jobs/%s.log" % t.jobid,
            "description": t.task.description_from(*t.args, **t.kw),
            "summary": t.task.summary,
            "name": t.task.name,
            "jobid": t.jobid,
        }

    def tearDown(t):
        del t.task
        del t.args
        del t.kw
        del t.jobid
        del t.expected

    def test_bad_jobid(t):
        with t.assertRaises(ValueError):
            build_redis_record(t.task, None, (), {})

    def test_minimum_args(t):
        actual = build_redis_record(t.task, t.jobid, t.args, t.kw)
        t.assertDictEqual(t.expected, actual)

    def test_non_default_description(t):
        description = "alternate description"
        t.expected["description"] = description
        actual = build_redis_record(
            t.task, t.jobid, t.args, t.kw, description=description,
        )
        t.assertDictEqual(t.expected, actual)

    def test_status(t):
        status = "PENDING"
        t.expected["status"] = status
        actual = build_redis_record(
            t.task, t.jobid, t.args, t.kw, status=status,
        )
        t.assertDictEqual(t.expected, actual)

    def test_created(t):
        created = 1234970434.303
        t.expected["created"] = created
        actual = build_redis_record(
            t.task, t.jobid, t.args, t.kw, created=created,
        )
        t.assertDictEqual(t.expected, actual)

    def test_userid(t):
        userid = "someuser"
        t.expected["userid"] = userid
        actual = build_redis_record(
            t.task, t.jobid, t.args, t.kw, userid=userid,
        )
        t.assertDictEqual(t.expected, actual)

    def test_details(t):
        details = {"a": 1, "b": 2}
        t.expected["details"] = details
        actual = build_redis_record(
            t.task, t.jobid, t.args, t.kw, details=details,
        )
        t.assertDictEqual(t.expected, actual)

    def test_all_defaulted_args(t):
        status = "PENDING"
        created = 1234970434.303
        userid = "someuser"
        details = {"a": 1, "b": 2}
        t.expected.update({
            "status": status,
            "created": created,
            "userid": userid,
            "details": details,
        })
        actual = build_redis_record(
            t.task, t.jobid, t.args, t.kw,
            status=status, created=created, userid=userid, details=details,
        )
        t.assertDictEqual(t.expected, actual)


class BuildRedisRecordFromJobTest(BaseBuildRedisRecord, TestCase):
    """Test the build_redis_record function with a Job."""

    class TestJob(Job):

        @classmethod
        def getJobType(cls):
            return "Test Job"

        @classmethod
        def getJobDescription(cls, *args, **kw):
            return "TestJob %s %s" % (args, kw)

    def setUp(t):
        t.task = t.TestJob()
        BaseBuildRedisRecord.setUp(t)


class BuildRedisRecordFromZenTaskTest(BaseBuildRedisRecord, TestCase):
    """Test the build_redis_record function with a ZenTask."""

    @app.task(
        bind=True,
        name="zen.zenjobs.test.test_task",
        summary="Test ZenTask",
        description_template="Test {0} named={named}",
    )
    def noop_task(self, *args, **kw):
        pass

    def setUp(t):
        t.task = t.noop_task
        BaseBuildRedisRecord.setUp(t)


class UpdateJobStatusTest(TestCase):

    layer = RedisLayer

    initial = {
        "jobid": "123",
        "name": "TestJob",
        "summary": "Products.Jobber.jobs.TestJob",
        "description": "A test job",
        "userid": "zenoss",
        "logfile": "/opt/zenoss/log/jobs/123.log",
        "created": 1551804881.024517,
        "status": "PENDING",
    }

    def setUp(t):
        t.store = JobStore(t.layer.redis)
        t.store[t.initial["jobid"]] = t.initial
        getGlobalSiteManager().registerUtility(
            t.store, IJobStore, name="redis",
        )

    def tearDown(t):
        t.layer.redis.flushall()
        getGlobalSiteManager().unregisterUtility(
            t.store, IJobStore, name="redis",
        )
        del t.store

    @patch("Products.Jobber.model.app.backend", autospec=True)
    def test_no_such_task(t, _backend):
        update_job_status("1")
        _backend.get_status.assert_not_called()

    @patch("Products.Jobber.model.time", autospec=True)
    @patch("Products.Jobber.model.app.backend", autospec=True)
    def test_unready_state(t, _backend, _time):
        tm = 1597059131.762538
        _backend.get_status.return_value = states.STARTED
        _time.time.return_value = tm

        expected_status = states.STARTED
        expected_started = tm
        expected_finished = None

        jobid = t.initial["jobid"]
        update_job_status(jobid)

        status = t.store.getfield(jobid, "status")
        started = t.store.getfield(jobid, "started")
        finished = t.store.getfield(jobid, "finished")

        t.assertEqual(expected_status, status)
        t.assertEqual(expected_started, started)
        t.assertEqual(expected_finished, finished)

    @patch("Products.Jobber.model.time", autospec=True)
    @patch("Products.Jobber.model.app.backend", autospec=True)
    def test_ready_state(t, _backend, _time):
        tm = 1597059131.762538
        _backend.get_status.return_value = states.SUCCESS
        _time.time.return_value = tm

        expected_status = states.SUCCESS
        expected_started = None
        expected_finished = tm

        jobid = t.initial["jobid"]
        update_job_status(jobid)

        status = t.store.getfield(jobid, "status")
        started = t.store.getfield(jobid, "started")
        finished = t.store.getfield(jobid, "finished")

        t.assertEqual(expected_status, status)
        t.assertEqual(expected_started, started)
        t.assertEqual(expected_finished, finished)

    @patch("Products.Jobber.model.time", autospec=True)
    @patch("Products.Jobber.model.app.backend", autospec=True)
    def test_task_aborted_state(t, _backend, _time):
        tm = 1597059131.762538
        _backend.get_status.return_value = states.ABORTED
        _time.time.return_value = tm

        expected_status = states.ABORTED
        expected_started = None
        expected_finished = tm

        jobid = t.initial["jobid"]
        update_job_status(jobid)

        status = t.store.getfield(jobid, "status")
        started = t.store.getfield(jobid, "started")
        finished = t.store.getfield(jobid, "finished")

        t.assertEqual(expected_status, status)
        t.assertEqual(expected_started, started)
        t.assertEqual(expected_finished, finished)

    @patch("Products.Jobber.model.time", autospec=True)
    @patch("Products.Jobber.model.app.backend", autospec=True)
    def test_job_aborted_state(t, _backend, _time):
        tm = 1597059131.762538
        _backend.get_status.return_value = states.FAILURE
        _time.time.return_value = tm

        jobid = t.initial["jobid"]
        t.store.update(jobid, status=states.ABORTED)

        expected_status = states.ABORTED
        expected_started = None
        expected_finished = tm

        update_job_status(jobid)

        status = t.store.getfield(jobid, "status")
        started = t.store.getfield(jobid, "started")
        finished = t.store.getfield(jobid, "finished")

        t.assertEqual(expected_status, status)
        t.assertEqual(expected_started, started)
        t.assertEqual(expected_finished, finished)


class ComponentsLoadedLayer(object):

    @classmethod
    def setUp(cls):
        from Zope2.App import zcml
        import Globals  # noqa: F401
        import Products.ZenWidgets
        from OFS.Application import import_products
        from Products.ZenUtils.Utils import load_config_override

        import_products()
        zcml.load_site()
        load_config_override('scriptmessaging.zcml', Products.ZenWidgets)


class JobRecordMarshallerTest(TestCase):
    """Test the JobRecordMarshaller class."""

    layer = ComponentsLoadedLayer

    def setUp(t):
        t.jobid = "12345"
        t.fields = {
            "description": "A test job record",
            "summary": "A Test",
            "name": "test",
            "jobid": t.jobid,
        }
        t.allfields = dict(t.fields, **{
            "status": None,
            "created": None,
            "finished": None,
            "started": None,
            "userid": None,
        })
        t.record = JobRecord.make(t.fields)

    def test_default_marshal(t):
        expected = {
            k: t.allfields[k]
            for k in JobRecordMarshaller._default_keys
            if k in t.allfields
        }
        serialized = marshal(t.record)
        t.assertDictEqual(expected, serialized)

    def test_keyed_marshal(t):
        keys = ("uuid", "name", "description")
        expected = {
            "uuid": t.allfields["jobid"],
            "name": t.allfields["name"],
            "description": t.allfields["description"],
        }
        serialized = marshal(t.record, keys=keys)
        t.assertDictEqual(expected, serialized)


class LegacySuportTest(TestCase):
    """Test the LegacySupport class."""

    def test_new_keys(t):
        keys = (
            "jobid",
            "name",
            "summary",
            "description",
            "userid",
            "logfile",
            "created",
            "started",
            "finished",
            "status",
        )
        for key in keys:
            with subTest(key=key):
                actual = LegacySuport.from_key(key)
                t.assertEqual(key, actual)

    def test_legacy_keys(t):
        keys = {
            "uuid": "jobid",
            "scheduled": "created",
            "user": "userid",
        }
        for key in keys:
            with subTest(key=key):
                actual = LegacySuport.from_key(key)
                t.assertEqual(keys[key], actual)
