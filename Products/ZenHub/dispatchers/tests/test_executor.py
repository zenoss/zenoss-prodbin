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
from mock import Mock
from twisted.internet import defer
from twisted.python.failure import Failure

from ..executor import (
    IAsyncDispatch, DispatchingExecutor, NoDispatchRoutes
)


class DispatchingExecutorTest(TestCase):

    def test___init__no_args(self):
        executor = DispatchingExecutor()
        self.assertEqual(None, executor.default)
        self.assertEqual((), executor.dispatchers)

    def test___init__custom_default(self):
        default = Mock()
        executor = DispatchingExecutor(default=default)
        self.assertEqual(default, executor.default)
        self.assertEqual((), executor.dispatchers)

    def test___init__with_dispatcher_no_default(self):
        dispatcher = Mock()
        dispatcher.routes = (("service", "method"),)
        executor = DispatchingExecutor([dispatcher])

        self.assertEqual(None, executor.default)
        self.assertEqual((dispatcher,), executor.dispatchers)

    def test___init__with_dispatcher_and_default(self):
        dispatcher = Mock()
        dispatcher.routes = (("service", "method"),)
        default = Mock()
        executor = DispatchingExecutor([dispatcher], default=default)

        self.assertEqual(default, executor.default)
        self.assertEqual((dispatcher,), executor.dispatchers)

    def test_register_new_dispatcher(self):
        executor = DispatchingExecutor()
        dispatcher = Mock()
        dispatcher.routes = (("service", "method"),)

        executor.register(dispatcher)

        self.assertEqual(None, executor.default)
        self.assertEqual((dispatcher,), executor.dispatchers)

    def test_register_dispatcher_missing_routes_attr(self):
        executor = DispatchingExecutor()
        dispatcher = Mock(spec=["submit"])  # missing 'routes'

        with self.assertRaises(AttributeError):
            executor.register(dispatcher)

    def test_register_dispatcher_routes_not_dictionary_like(self):
        executor = DispatchingExecutor()
        dispatcher = Mock(spec=IAsyncDispatch.names())

        with self.assertRaises(Exception):
            executor.register(dispatcher)

    def test_register_dispatcher_no_routes_specified(self):
        executor = DispatchingExecutor()
        dispatcher = Mock(spec=IAsyncDispatch.names())
        dispatcher.routes = {}

        with self.assertRaises(NoDispatchRoutes):
            executor.register(dispatcher)

    def test_register_dispatcher_with_duplicate_route(self):
        executor = DispatchingExecutor()
        dispatcher1 = Mock(spec=IAsyncDispatch.names())
        dispatcher1.routes = (("service", "method"),)
        dispatcher2 = Mock(spec=IAsyncDispatch.names())
        dispatcher2.routes = (("service", "method"),)

        executor.register(dispatcher1)

        with self.assertRaises(ValueError):
            executor.register(dispatcher2)

    def test_set_default_dispatcher(self):
        executor = DispatchingExecutor()
        dispatcher = Mock(spec=IAsyncDispatch.names())

        executor.default = dispatcher

        self.assertEqual(dispatcher, executor.default)
        self.assertEqual((), executor.dispatchers)

    def test_replace_default_dispatcher(self):
        original_default = Mock(spec=IAsyncDispatch.names())
        executor = DispatchingExecutor(default=original_default)
        dispatcher = Mock(spec=IAsyncDispatch.names())

        executor.default = dispatcher

        self.assertEqual(dispatcher, executor.default)
        self.assertEqual((), executor.dispatchers)

    def test_submit_job_with_matching_dispatcher(self):
        dispatcher = Mock()
        dispatcher.routes = (("service", "method"),)
        executor = DispatchingExecutor([dispatcher])
        job = Mock(service="service", method="method")

        dfr = executor.submit(job)

        self.assertIsInstance(dfr, defer.Deferred)
        dispatcher.submit.assert_called_once_with(job)
        self.assertEqual(dfr.result, dispatcher.submit.return_value)

    def test_submit_job_to_default_dispatcher(self):
        default = Mock(spec=IAsyncDispatch.names())
        dispatcher = Mock(spec=IAsyncDispatch.names())
        dispatcher.routes = (("service", "methodA"),)
        executor = DispatchingExecutor([dispatcher], default=default)
        job = Mock(service="service", method="methodB")

        dfr = executor.submit(job)

        self.assertIsInstance(dfr, defer.Deferred)
        dispatcher.submit.assert_not_called()
        default.submit.assert_called_once_with(job)
        self.assertEqual(dfr.result, default.submit.return_value)

    def test_submit_job_with_no_route_no_default(self):
        dispatcher = Mock()
        dispatcher.routes = (("service", "methodA"),)
        executor = DispatchingExecutor([dispatcher])
        job = Mock(service="service", method="methodB")

        handler = Mock()
        dfr = executor.submit(job)
        dfr.addErrback(handler)

        self.assertEqual(len(handler.mock_calls), 1)

        f = handler.call_args[0][0]
        self.assertIsInstance(f, Failure)
        self.assertIsInstance(f.value, RuntimeError)
        self.assertRegexpMatches(str(f.value), ".*methodB.*")
        dispatcher.submit.assert_not_called()
