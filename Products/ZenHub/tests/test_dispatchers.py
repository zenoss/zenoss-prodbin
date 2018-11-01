##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from unittest import TestCase

from .. import dispatchers
from ..dispatchers.base import IAsyncDispatch
from ..dispatchers.executor import DispatchingExecutor, NoDispatchRoutes
from ..dispatchers.event import EventDispatcher
from ..dispatchers.workers import (
    WorkerPoolDispatcher, ServiceCallJob, StatsMonitor
)
from ..dispatchers.workerpool import WorkerPool


def _get(attr):
    return getattr(dispatchers, attr, None)


class DispatchersPackageTest(TestCase):
    """
    """

    def test_has_required_attributes(self):
        self.assertIs(IAsyncDispatch, _get("IAsyncDispatch"))
        self.assertIs(DispatchingExecutor, _get("DispatchingExecutor"))
        self.assertIs(NoDispatchRoutes, _get("NoDispatchRoutes"))
        self.assertIs(EventDispatcher, _get("EventDispatcher"))
        self.assertIs(WorkerPoolDispatcher, _get("WorkerPoolDispatcher"))
        self.assertIs(ServiceCallJob, _get("ServiceCallJob"))
        self.assertIs(StatsMonitor, _get("StatsMonitor"))
        self.assertIs(WorkerPool, _get("WorkerPool"))
