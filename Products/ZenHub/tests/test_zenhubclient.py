##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from mock import Mock, patch, sentinel
from unittest import TestCase

from twisted.internet import reactor

from Products.ZenHub.zenhubclient import ZenHubClient

PATH = {"src": "Products.ZenHub.zenhubclient"}


class ZenHubClientTest(TestCase):
    """Test the ZenHubClient class."""

    def setUp(t):
        t.reactor = Mock(reactor, autospec=True)
        t.endpoint = sentinel.endpoint
        t.credentials = Mock()
        t.app = Mock()
        t.timeout = 10
        t.worklistId = "default"

        # Patch external dependencies
        needs_patching = [
            "ClientService",
            "setKeepAlive",
            "ZenPBClientFactory",
        ]
        t.patchers = {}
        for target in needs_patching:
            patched = patch(
                "{src}.{target}".format(target=target, **PATH),
                autospec=True,
            )
            t.patchers[target] = patched
            name = target.rpartition(".")[-1]
            setattr(t, name, patched.start())
            t.addCleanup(patched.stop)

        t.zhc = ZenHubClient(
            t.app,
            t.endpoint,
            t.credentials,
            t.timeout,
            reactor=t.reactor,
        )

    def test_initial_state(t):
        t.assertFalse(t.zhc.is_connected)
        t.assertIsNone(t.zhc.instance_id)
        t.assertEqual(len(t.zhc.services), 0)

    def test_start(t):
        d = t.zhc.start()

        t.assertIs(d, t.ClientService.return_value.whenConnected.return_value)
        client = t.ClientService.return_value
        client.startService.assert_called_once_with()

    def test_stop(t):
        d = t.zhc.stop()

        t.assertIs(d, t.ClientService.return_value.stopService.return_value)
        t.assertFalse(t.zhc.is_connected)
        t.assertEqual(len(t.zhc.services), 0)
