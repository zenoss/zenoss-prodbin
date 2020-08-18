##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import inspect

from mock import patch
from unittest import TestCase
from zope.component import getGlobalSiteManager

from ..interfaces import IJobStore
from ..manager import JobManager
from ..storage import JobStore
from .utils import subTest, RedisLayer


class JobManagerTest(TestCase):
    """Test the JobManager class."""

    layer = RedisLayer

    full = {
        "jobid": "123",
        "name": "TestJob",
        "summary": "Products.Jobber.jobs.TestJob",
        "description": "A test job",
        "userid": "zenoss",
        "logfile": "/opt/zenoss/log/jobs/123.log",
        "created": 1551804881.024517,
        "started": 1551804891.863857,
        "finished": 1551805270.154359,
        "status": "SUCCESS",
    }

    def setUp(t):
        t.manager = JobManager("JobManagerTest")
        t.store = JobStore(t.layer.redis)
        getGlobalSiteManager().registerUtility(
            t.store, IJobStore, name="redis",
        )

    def tearDown(t):
        t.layer.redis.flushall()
        getGlobalSiteManager().unregisterUtility(
            t.store, IJobStore, name="redis",
        )
        del t.store
        del t.manager

    def test_api_existence(t):
        methods = (
            "addJobChain",
            "addJob",
            "wait",
            "query",
            "update",
            "getJob",
            "deleteJob",
            "getUnfinishedJobs",
            "getRunningJobs",
            "getPendingJobs",
            "getFinishedJobs",
            "getAllJobs",
            "clearJobs",
            "killRunning",
        )
        for name in methods:
            with subTest(method_name=name):
                method = getattr(JobManager, name, None)
                t.assertTrue(inspect.ismethod(method))
        all_methods = set(
            m for m in JobManager.__dict__
            if not m.startswith("_")
            and inspect.ismethod(getattr(JobManager, m, None))
        )
        missing = all_methods - set(methods)
        t.assertSetEqual(
            set({}),
            missing,
            "JobManager has some new methods since the last time this "
            "test was updated. Please update this test to include the "
            "new methods.",
        )

    def test_query_bad_criteria(t):
        with t.assertRaises(ValueError):
            t.manager.query(criteria={"blah": 1})

    def test_query_good_criteria(t):
        keys = {
            "status": "STARTED",
            "user": "joe",
            "userid": "joe",
        }
        for key, value in keys.items():
            criteria = {key: value}
            with subTest(criteria=criteria):
                t.manager.query(criteria=criteria)

    def test_good_sort_keys(t):
        t.store[t.full["jobid"]] = t.full
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
            "uuid",
            "scheduled",
            "user",
        )
        for key in keys:
            with subTest(key=key):
                t.manager.query(key=key)

    def test_bad_sort_key(t):
        with t.assertRaises(ValueError):
            t.manager.query(key="details")

    def test_query_return_value(t):
        expected = {"jobs": (), "total": 0}
        actual = t.manager.query()
        t.assertDictEqual(expected, actual)
