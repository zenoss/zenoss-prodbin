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

from ..events import (
    ServiceCallEvent, ServiceCallReceived, ServiceCallStarted,
    ServiceCallCompleted,
)
from ..utils import subTest


class ServiceCallEventTest(TestCase):
    """Test the ServiceCallEvent class."""

    def test_attribute_names(self):
        event = ServiceCallEvent()
        expected = []
        names = sorted(n for n in dir(event) if not n.startswith("_"))
        self.assertSequenceEqual(expected, names)

    def test_for_slots(self):
        self.assertTrue(hasattr(ServiceCallEvent, "__slots__"))


class ServiceCallReceivedTest(TestCase):
    """Test the ServiceCallReceived class."""

    def test_for_slots(self):
        self.assertTrue(hasattr(ServiceCallReceived, "__slots__"))

    def test_default_values(self):
        event = ServiceCallReceived()
        self.assertTrue(all(
            getattr(event, name) is None
            for name in ServiceCallReceived.__slots__
        ))

    def test_expected_init_args(self):
        names = (
            "id", "monitor", "service", "method", "args", "kwargs",
            "timestamp", "queue", "priority",
        )
        args = {k: None for k in names}
        ServiceCallReceived(**args)

    def test_no_extra_init_args(self):
        args = ("worker", "attempts", "error", "retry", "result", "foo")
        for arg in args:
            with subTest(arg=arg):
                with self.assertRaises(AssertionError):
                    ServiceCallReceived(**{arg: None})


class ServiceCallStartedTest(TestCase):
    """Test the ServiceCallStarted class."""

    def test_for_slots(self):
        self.assertTrue(hasattr(ServiceCallStarted, "__slots__"))

    def test_default_values(self):
        event = ServiceCallStarted(attempts=1)
        self.assertTrue(all(
            getattr(event, name) is None
            for name in ServiceCallEvent.__slots__
            if name != "attempts"
        ))
        self.assertEqual(1, event.attempts)

    def test_expected_init_args(self):
        names = (
            "id", "monitor", "service", "method", "args", "kwargs",
            "timestamp", "queue", "priority", "worker",
        )
        args = {k: None for k in names}
        args["attempts"] = 1
        ServiceCallStarted(**args)

    def test_no_extra_init_args(self):
        tests = ("error", "retry", "result", "foo")
        for test in tests:
            with subTest(test=test):
                args = {"attempts": 1, test: None}
                with self.assertRaises(AssertionError):
                    ServiceCallStarted(**args)


class ServiceCallCompletedTest(TestCase):
    """Test the ServiceCallCompleted class."""

    def test_for_slots(self):
        self.assertTrue(hasattr(ServiceCallCompleted, "__slots__"))

    def test_mismatched_arguments(self):
        exc = RuntimeError()
        result = 10
        tests = (
            {"attempts": 0},
            {"attempts": 0, "error": exc},
            {"attempts": 0, "retry": exc},
            {"attempts": 0, "result": result},
            {"attempts": 0, "error": exc, "retry": exc},
            {"attempts": 1},
            {"attempts": 1, "result": result, "error": exc, "retry": exc},
            {"attempts": 1, "error": exc, "result": result},
        )
        for args in tests:
            with subTest(args=args):
                with self.assertRaises(AssertionError):
                    ServiceCallCompleted(**args)

    def test_nominal_init_failure(self):
        exc = RuntimeError()
        event = ServiceCallCompleted(attempts=1, error=exc)
        self.assertTrue(all(
            getattr(event, name) is None
            for name in ServiceCallEvent.__slots__
            if name not in ("attempts", "error")
        ))
        self.assertEqual(1, event.attempts)
        self.assertIs(exc, event.error)

    def test_nominal_init_retry(self):
        exc = RuntimeError()
        event = ServiceCallCompleted(attempts=1, retry=exc)
        self.assertTrue(all(
            getattr(event, name) is None
            for name in ServiceCallEvent.__slots__
            if name not in ("attempts", "retry")
        ))
        self.assertEqual(1, event.attempts)
        self.assertIs(exc, event.retry)

    def test_nominal_init_success(self):
        result = 10
        event = ServiceCallCompleted(attempts=1, result=result)
        self.assertTrue(all(
            getattr(event, name) is None
            for name in ServiceCallEvent.__slots__
            if name not in ("attempts", "result")
        ))
        self.assertEqual(1, event.attempts)
        self.assertIs(result, event.result)

    def test_no_extra_init_args(self):
        with self.assertRaises(AssertionError):
            ServiceCallCompleted(attempts=1, foo=10)
