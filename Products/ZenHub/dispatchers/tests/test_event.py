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
from mock import Mock, patch
from twisted.internet import defer
from twisted.python.failure import Failure

from Products.ZenEvents.MySqlEventManager import MySqlEventManager

from ..event import EventDispatcher

PATH = {'src': 'Products.ZenHub.dispatchers.event'}


class EventDispatcherTest(TestCase):

    def setUp(self):
        self.em = Mock(spec=MySqlEventManager)
        self.dispatcher = EventDispatcher(self.em)

    def test_routes(self):
        routes = (
            ("EventService", "sendEvent"), ("EventService", "sendEvents")
        )
        self.assertSequenceEqual(routes, EventDispatcher.routes)

    def test_sendEvent_job(self):
        job = Mock(
            service="EventService", method="sendEvent",
            args=["event"], kwargs={}
        )

        dfr = self.dispatcher.submit(job)

        self.assertIsInstance(dfr, defer.Deferred)
        self.assertEqual(self.em.sendEvent.return_value, dfr.result)
        self.em.sendEvent.assert_called_once_with("event")
        self.em.sendEvents.assert_not_called()

    def test_sendEvents_job(self):
        job = Mock(
            service="EventService", method="sendEvents",
            args=[["event"]], kwargs={}
        )

        dfr = self.dispatcher.submit(job)

        self.assertIsInstance(dfr, defer.Deferred)
        self.assertEqual(self.em.sendEvents.return_value, dfr.result)
        self.em.sendEvents.assert_called_once_with(["event"])
        self.em.sendEvent.assert_not_called()

    @patch("{src}.getattr".format(**PATH))
    def test_bad_job(self, mock_getattr):
        job = Mock(
            service="EventService", method="badmethod",
            args=[["event"]], kwargs={}
        )

        mock_getattr.return_value = None

        handler = Mock()
        dfr = self.dispatcher.submit(job)
        dfr.addErrback(handler)

        self.assertEqual(len(handler.mock_calls), 1)

        f = handler.call_args[0][0]
        self.assertIsInstance(f, Failure)
        self.assertIsInstance(f.value, AttributeError)
        self.assertRegexpMatches(str(f.value), ".*badmethod.*")

        self.em.sendEvent.assert_not_called()
        self.em.sendEvents.assert_not_called()

    def test_exception_from_service(self):
        job = Mock(
            service="EventService", method="sendEvent", args=[], kwargs={}
        )

        error = ValueError("boom")
        self.em.sendEvent.side_effect = error

        handler = Mock()
        dfr = self.dispatcher.submit(job)
        dfr.addErrback(handler)

        self.assertEqual(len(handler.mock_calls), 1)

        f = handler.call_args[0][0]
        self.assertIsInstance(f, Failure)
        self.assertIsInstance(f.value, ValueError)
        self.assertEqual(str(f.value), "boom")

        self.em.sendEvent.assert_called_once_with()
        self.em.sendEvents.assert_not_called()
