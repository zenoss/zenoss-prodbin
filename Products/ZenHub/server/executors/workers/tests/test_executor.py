##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import collections
import itertools

from unittest import TestCase
from mock import (
    MagicMock,
    Mock,
    NonCallableMagicMock,
    patch,
)

from twisted.internet import reactor
from twisted.internet.defer import Deferred

from Products.ZenHub.server.config import ModuleObjectConfig
from Products.ZenHub.server.service import ServiceCall
from Products.ZenHub.server.workerpool import WorkerPool
from Products.ZenHub.server.utils import subTest

from ..executor import (
    Scheduler,
    ServiceCallPriority,
    WorkerPoolExecutor,
    ZenHubWorklist,
)

PATH = {"src": "Products.ZenHub.server.executors.workers.executor"}


class _PrioritySelection(collections.Iterator):

    def __init__(self):
        self.priorities = tuple(ServiceCallPriority)
        self.available = tuple(ServiceCallPriority)
        self._iter = itertools.cycle(self.priorities)

    def next(self):
        return next(self._iter)


class WorkerPoolExecutorTest(TestCase):  # noqa: D101
    def setUp(t):
        t.getLogger_patcher = patch(
            "{src}.getLogger".format(**PATH),
            autospec=True,
        )
        t.getLogger = t.getLogger_patcher.start()
        t.addCleanup(t.getLogger_patcher.stop)

        t.loopingCall_patcher = patch(
            "{src}.LoopingCall".format(**PATH),
            autospec=True,
        )
        t.loopingCall = t.loopingCall_patcher.start()
        t.addCleanup(t.loopingCall_patcher.stop)

        t.reactor = Mock(spec=reactor)
        t.worklist = ZenHubWorklist(_PrioritySelection())
        t.workers = NonCallableMagicMock(spec=WorkerPool)

        t.name = "default"
        t.executor = WorkerPoolExecutor(
            t.name,
            t.worklist,
            t.workers,
        )
        t.logger = t.getLogger(t.executor)

    def test_create_requires_pool_and_config_args(t):
        cases = {
            "missing 'config' and 'pool'": {},
            "missing 'config'": {"pool": t.workers},
            "missing 'pool'": {"config": Mock()},
        }
        for name, params in cases.items():
            with subTest(case=name):
                with t.assertRaises(ValueError):
                    WorkerPoolExecutor.create(t.name, **params)

    @patch("{src}.ModelingPaused".format(**PATH), autospec=True)
    @patch("{src}.PrioritySelection".format(**PATH), autospec=True)
    @patch("{src}.ZenHubWorklist".format(**PATH), autospec=True)
    def test_create(t, _zhwlist, _ps, _mp):
        config = MagicMock(spec=ModuleObjectConfig)
        pool = Mock()

        result = WorkerPoolExecutor.create(t.name, config, pool)

        _mp.assert_called_once_with(
            config.priorities["modeling"],
            config.modeling_pause_timeout,
        )
        _ps.assert_called_once_with(
            ServiceCallPriority,
            exclude=_mp.return_value,
        )
        _zhwlist.assert_called_once_with(_ps.return_value)
        t.assertIsInstance(result, WorkerPoolExecutor)
        t.assertEqual(result.name, t.name)
        t.assertEqual(result.pool, pool)
        t.assertIsInstance(result.worklist, ZenHubWorklist)
        t.assertIsNone(result.scheduler)

    def test_start(t):
        t.executor.start(t.reactor)
        t.assertIsInstance(t.executor.scheduler, Scheduler)
        t.loopingCall.assert_called_once_with(t.executor.scheduler)

    def test_start_again(t):
        t.executor.start(t.reactor)
        first_scheduler = t.executor.scheduler

        t.executor.start(t.reactor)  # effectively a no-op
        second_scheduler = t.executor.scheduler

        t.assertIs(first_scheduler, second_scheduler)

    def test_submit_before_start(t):
        call = Mock(spec=ServiceCall)

        with t.assertRaises(RuntimeError):
            t.executor.submit(call)

    def test_submit(t):
        call = Mock(spec=ServiceCall)
        call.monitor = "localhost"
        call.service = "PingPerf"
        call.method = "getStuff"
        t.executor.start(t.reactor)

        submitd = t.executor.submit(call)

        t.assertIsInstance(submitd, Deferred)
        t.assertEqual(len(t.worklist), 1)

        popd = t.worklist.pop()
        task = popd.result
        t.assertIs(task.call, call)
        t.assertEqual(task.worklist, t.name)
        t.assertIsInstance(task.received_tm, float)
        t.assertEqual(task.max_retries, 3)
        t.assertEqual(task.attempt, 0)
        t.assertIsNone(task.started_tm)
        t.assertIsNone(task.completed_tm)
        t.assertIsNone(task.worker_name)

    def test_stop_before_start(t):
        t.executor.stop()
        t.assertIsNone(t.executor.scheduler)

    def test_stop(t):
        t.executor.start(t.reactor)
        t.executor.stop()
        t.assertIsNone(t.executor.scheduler)
