##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from unittest import TestCase
from mock import Mock, patch, create_autospec, sentinel

from ..avatar import HubAvatar, RemoteBadMonitor, pb
from ..service import ServiceManager
from ..workerpool import WorkerPool

PATH = {"src": "Products.ZenHub.server.avatar"}


class HubAvatarTest(TestCase):
    """Test the HubAvatar class."""

    def setUp(self):
        self.getLogger_patcher = patch(
            "{src}.getLogger".format(**PATH),
            autospec=True,
        )
        self.getLogger = self.getLogger_patcher.start()
        self.addCleanup(self.getLogger_patcher.stop)

        self.services = create_autospec(ServiceManager)
        self.pools = {
            "foo": create_autospec(WorkerPool),
            "bar": create_autospec(WorkerPool),
        }
        self.avatar = HubAvatar(self.services, self.pools)

    def test_perspective_ping(self):
        ret = self.avatar.perspective_ping()
        self.assertEqual(ret, "pong")

    @patch("{src}.os.environ".format(**PATH), name="os.environ", autospec=True)
    def test_perspective_getHubInstanceId_normal(self, os_environ):
        key = "CONTROLPLANE_INSTANCE_ID"
        hubId = "hub"

        def side_effect(k, d):
            if k == key:
                return hubId
            return d

        os_environ.get.side_effect = side_effect

        actual = self.avatar.perspective_getHubInstanceId()

        self.assertEqual(actual, hubId)

    @patch("{src}.os.environ".format(**PATH), name="os.environ", autospec=True)
    def test_perspective_getHubInstanceId_unknown(self, os_environ):
        os_environ.get.side_effect = lambda k, d: d
        actual = self.avatar.perspective_getHubInstanceId()
        self.assertEqual(actual, "Unknown")

    def test_perspective_getService_no_listener(self):
        service_name = "testservice"
        monitor = "localhost"

        expected = self.services.getService.return_value
        actual = self.avatar.perspective_getService(service_name, monitor)

        self.services.getService.assert_called_with(service_name, monitor)
        expected.addListener.assert_not_called()
        self.assertEqual(expected, actual)

    def test_perspective_getService_with_listener(self):
        service_name = "testservice"
        monitor = "localhost"
        listener = sentinel.listener
        options = sentinel.options

        expected = self.services.getService.return_value
        actual = self.avatar.perspective_getService(
            service_name,
            monitor,
            listener=listener,
            options=options,
        )

        self.services.getService.assert_called_with(service_name, monitor)
        expected.addListener.assert_called_once_with(listener, options)
        self.assertEqual(expected, actual)

    def test_perspective_getService_raises_RemoteBadMonitor(self):
        self.services.getService.side_effect = RemoteBadMonitor("tb", "msg")
        with self.assertRaises(RemoteBadMonitor):
            self.avatar.perspective_getService("service_name")

    @patch("{src}.getLogger".format(**PATH))
    def test_perspective_getService_raises_error(self, getLogger):
        logger = getLogger.return_value
        self.avatar._HubAvatar__log = logger
        service_name = "service_name"
        self.services.getService.side_effect = Exception()

        with self.assertRaises(pb.Error):
            self.avatar.perspective_getService(service_name)
            logger.exception.assert_called_once_with(
                "Failed to get service '%s'",
                service_name,
            )

    def test_perspective_reportingForWork_nominal(self):
        worker = Mock(
            spec_set=[
                "workerId",
                "sessionId",
                "queue_name",
                "notifyOnDisconnect",
            ]
        )
        workerId = "default-1"

        disconnect_callback = []

        def _notifyOnDisconnect(callback):
            disconnect_callback.append(callback)

        worker.notifyOnDisconnect.side_effect = _notifyOnDisconnect

        # Add the worker
        self.avatar.perspective_reportingForWork(worker, workerId, "foo")
        self.assertTrue(hasattr(worker, "sessionId"))
        self.assertIsNotNone(worker.sessionId)
        self.assertTrue(hasattr(worker, "workerId"))
        self.assertEqual(worker.workerId, workerId)
        self.pools["foo"].add.assert_called_once_with(worker)

        # Remove the worker
        self.assertEqual(
            1,
            len(disconnect_callback),
            "notifyOnDisconnect not called",
        )
        disconnect_callback[0](worker)
        self.pools["foo"].remove.assert_called_once_with(worker)
