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
import logging
import types

from celery import states
from mock import patch
from unittest import TestCase

from zope.component import getGlobalSiteManager

from ..model import (
    app,
    IJobStore,
    job_start,
    job_end,
    job_success,
    job_failure,
    job_retry,
)
from ..storage import JobStore, Fields
from .utils import subTest, RedisLayer

UNEXPECTED = type("UNEXPECTED", (object,), {})()
PATH = {"src": "Products.Jobber.model"}


class _CommonFixture(object):

    jobid = "123"

    initial = {
        "jobid": jobid,
        "name": "TestJob",
        "summary": "Products.Jobber.jobs.TestJob",
        "description": "A test job",
        "userid": "zenoss",
        "logfile": "/opt/zenoss/log/jobs/%s.log" % jobid,
        "created": 1551804881.024517,
        "status": "PENDING",
    }

    def setUp(t):
        t.store = JobStore(t.layer.redis)
        t.store[t.jobid] = t.initial
        getGlobalSiteManager().registerUtility(
            t.store, IJobStore, name="redis",
        )
        rootLogger = logging.getLogger()
        t.handlers = rootLogger.handlers
        rootLogger.handlers = []

    def tearDown(t):
        t.layer.redis.flushall()
        getGlobalSiteManager().unregisterUtility(
            t.store, IJobStore, name="redis",
        )
        del t.store
        rootLogger = logging.getLogger()
        rootLogger.handlers = t.handlers
        del t.handlers


class JobStartTest(_CommonFixture, TestCase):

    layer = RedisLayer

    def test_unknown_task_id(t):
        job_start("1")

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_started(t, _time):
        tm = 1597059131.762538
        _time.time.return_value = tm

        expected_status = states.STARTED
        expected_started = tm
        expected_finished = None

        job_start(t.jobid)

        status = t.store.getfield(t.jobid, "status")
        started = t.store.getfield(t.jobid, "started")
        finished = t.store.getfield(t.jobid, "finished")

        t.assertEqual(expected_status, status)
        t.assertEqual(expected_started, started)
        t.assertEqual(expected_finished, finished)

    def test_already_aborted(t):
        expected_started = None
        expected_status = states.ABORTED
        t.store.update(t.jobid, status=expected_status)

        job_start(t.jobid)

        status = t.store.getfield(t.jobid, "status")
        started = t.store.getfield(t.jobid, "started")

        t.assertEqual(expected_status, status)
        t.assertEqual(expected_started, started)


class JobEndTest(_CommonFixture, TestCase):

    layer = RedisLayer

    def test_unknown_task_id(t):
        job_start("1")

    def test_job_not_finished(t):
        tm = 1597059131.762538
        t.store.update(t.jobid, started=tm)
        job_end(t.jobid)

    def test_job_finished(t):
        started_tm = 1597059131.762538
        finished_tm = started_tm + 10
        t.store.update(t.jobid, started=started_tm, finished=finished_tm)
        job_end(t.jobid)


class JobSuccessTest(_CommonFixture, TestCase):

    layer = RedisLayer

    def test_unknown_task_id(t):
        job_start("1")

    @patch("{src}.time".format(**PATH), autospec=True)
    @patch("{src}.app.backend".format(**PATH), autospec=True)
    def test_success(t, _backend, _time):
        tm = 1597059131.762538

        req = type("request", (object,), {"id": t.jobid})()
        sender = type(
            "sender",
            (object,),
            {"request": req, "ignore_result": False},
        )()

        expected_status = states.SUCCESS
        expected_started = tm - 10
        expected_finished = tm

        _backend.get_status.return_value = expected_status
        _time.time.return_value = expected_finished

        t.store.update(t.jobid, started=expected_started)

        job_success(None, sender=sender)

        status = t.store.getfield(t.jobid, "status")
        started = t.store.getfield(t.jobid, "started")
        finished = t.store.getfield(t.jobid, "finished")

        t.assertEqual(expected_status, status)
        t.assertEqual(expected_started, started)
        t.assertEqual(expected_finished, finished)


class JobFailureTest(_CommonFixture, TestCase):

    layer = RedisLayer

    def test_unknown_task_id(t):
        job_start("1")

    @patch("{src}.time".format(**PATH), autospec=True)
    @patch("{src}.app.backend".format(**PATH), autospec=True)
    def test_aborted(t, _backend, _time):
        tm = 1597059131.762538

        expected_status = states.ABORTED
        expected_started = None
        expected_finished = tm

        _backend.get_status.return_value = expected_status
        _time.time.return_value = expected_finished

        job_failure(t.jobid)

        status = t.store.getfield(t.jobid, "status")
        started = t.store.getfield(t.jobid, "started")
        finished = t.store.getfield(t.jobid, "finished")

        t.assertEqual(expected_status, status)
        t.assertEqual(expected_started, started)
        t.assertEqual(expected_finished, finished)

    @patch("{src}.time".format(**PATH), autospec=True)
    @patch("{src}.app.backend".format(**PATH), autospec=True)
    def test_failure(t, _backend, _time):
        tm = 1597059131.762538

        expected_status = states.FAILURE
        expected_started = None
        expected_finished = tm

        _backend.get_status.return_value = expected_status
        _time.time.return_value = expected_finished

        job_failure(t.jobid)

        status = t.store.getfield(t.jobid, "status")
        started = t.store.getfield(t.jobid, "started")
        finished = t.store.getfield(t.jobid, "finished")

        t.assertEqual(expected_status, status)
        t.assertEqual(expected_started, started)
        t.assertEqual(expected_finished, finished)

    @patch("{src}.time".format(**PATH), autospec=True)
    @patch("{src}.app.backend".format(**PATH), autospec=True)
    def test_callbacks_are_aborted(t, _backend, _time):
        next_jobid = "456"
        next_job = dict(t.initial)
        next_job["jobid"] = next_jobid
        t.store[next_jobid] = next_job

        request = type(
            "request",
            (object,),
            {"callbacks": [{"options": {"task_id": next_jobid}}]},
        )()
        sender = type(
            "task",
            (object,),
            {"request": request, "ignore_result": False},
        )()

        tm = 1597059131.762538

        expected_status = states.ABORTED
        expected_started = None
        expected_finished = tm

        _backend.get_status.return_value = expected_status
        _time.time.return_value = expected_finished

        job_failure(t.jobid, sender=sender)

        for jobid in (t.jobid, next_jobid):
            with subTest(jobid=jobid):
                status = t.store.getfield(jobid, "status")
                started = t.store.getfield(jobid, "started")
                finished = t.store.getfield(jobid, "finished")

                t.assertEqual(expected_status, status)
                t.assertEqual(expected_started, started)
                t.assertEqual(expected_finished, finished)


class JobRetryTest(_CommonFixture, TestCase):

    layer = RedisLayer

    def test_unknown_task_id(t):
        req = type("request", (object,), {"id": "1"})()
        job_retry(req)

    @patch("{src}.app.backend".format(**PATH), autospec=True)
    def test_nominal(t, _backend):
        tm = 1597059131.762538
        req = type("request", (object,), {"id": t.jobid})()

        expected_status = states.RETRY
        expected_started = tm
        expected_finished = None

        _backend.get_status.return_value = expected_status

        t.store.update(t.jobid, started=expected_started)
        job_retry(req)

        status = t.store.getfield(t.jobid, "status")
        started = t.store.getfield(t.jobid, "started")
        finished = t.store.getfield(t.jobid, "finished")

        t.assertEqual(expected_status, status)
        t.assertEqual(expected_started, started)
        t.assertEqual(expected_finished, finished)


class IgnoreResultTest(TestCase):
    """Test update_job_status when a task's ignore_result is True.
    """

    @app.task(
        bind=True,
        name="zen.zenjobs.test.result_ignored_task",
        summary="Result Ignored Task",
        ignore_result=True,
    )
    def noop_task(self, *args, **kw):
        pass

    @patch("{src}.getUtility".format(**PATH))
    def test_job_start(t, _getUtility):
        task = app.tasks.get("zen.zenjobs.test.result_ignored_task")
        job_start(task_id="0", task=task)
        _getUtility.assert_not_called()

    @patch("{src}.getUtility".format(**PATH))
    def test_job_end(t, _getUtility):
        task = app.tasks.get("zen.zenjobs.test.result_ignored_task")
        job_end(task_id="0", task=task)
        _getUtility.assert_not_called()

    @patch("{src}.getUtility".format(**PATH))
    def test_job_success(t, _getUtility):
        task = app.tasks.get("zen.zenjobs.test.result_ignored_task")
        job_success(None, sender=task)
        _getUtility.assert_not_called()

    @patch("{src}.getUtility".format(**PATH))
    def test_job_failure(t, _getUtility):
        task = app.tasks.get("zen.zenjobs.test.result_ignored_task")
        job_failure(task_id="0", sender=task)
        _getUtility.assert_not_called()

    @patch("{src}.getUtility".format(**PATH))
    def test_job_retry(t, _getUtility):
        task = app.tasks.get("zen.zenjobs.test.result_ignored_task")
        job_retry(None, sender=task)
        _getUtility.assert_not_called()
