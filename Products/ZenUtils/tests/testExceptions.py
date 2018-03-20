#!/usr/bin/env python

from unittest import TestCase

from twisted.spread.pb import RemoteError
from twisted.python.failure import Failure

from Products.ZenUtils.Exceptions import (
    resolveException, ZenPathError, ZenResolveExceptionError
)


class ExceptionTestCases(TestCase):

    def setUp(self):
        self.exception = RuntimeError('genric exception')
        self.failure = Failure(self.exception)

    def test_resolveException(self):
        out = resolveException(self.failure)
        self.assertEqual(out, self.exception)

    def test_resolveException_handles_twisted_spread_pb_RemoteError(self):
        '''pb RemoteError class takes additional arguments,
        which caused decoding to throw
        TypeError: __init__() takes exactly 4 arguments (3 given)
        '''
        exception = RemoteError('remoteType', 'value', 'remoteTraceback')
        failure = Failure(exception)
        out = resolveException(failure)
        self.assertIsInstance(out, RemoteError)
        self.assertEqual(out, exception)

    def test_resolve_exception_by_type(self):
        '''If resolving the exception from the Failure object fails,
        falls back to resolving it by the type string
        '''
        self.failure.value = None
        self.failure.type = "Products.ZenUtils.Exceptions.ZenPathError"
        self.failure.value = 'some string'
        self.failure.tb = 'traceback object'

        out = resolveException(self.failure)
        expected = ZenPathError(self.failure.value, self.failure.tb)

        self.assertIsInstance(out, ZenPathError)
        self.assertEqual(out.args, expected.args)

    def test_resolveException_unknown_error_type(self):
        '''Provides useful exception information for unresolvable error types
        '''
        self.failure.value = None
        self.failure.type = 'some.unknown.unresolvable.exception'
        self.failure.value = 'some string'
        self.failure.tb = 'traceback object'

        out = resolveException(self.failure)
        expected = ZenResolveExceptionError(
            self.failure.value, self.failure.tb, self.failure.__dict__
        )

        self.assertIsInstance(out, ZenResolveExceptionError)
        self.assertEqual(out.args, expected.args)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(ExceptionTestCases))
    return suite
