#!/usr/bin/env python

from unittest import TestCase

from Products.ZenUtils.Exceptions import (
    resolveException, ZentinelException, ZenPathError, ZenResolveExceptionError
)
from Products.ZenTestCase.BaseTestCase import BaseTestCase

from twisted.spread.pb import RemoteError
from twisted.python.failure import Failure


class DummyFailure(object):
    def __init__(self):
        self.value = None
        self.type = None
        self.tb = None
        self.raise_value = None

    def raiseException(self):
        raise self.raise_value, self.type, self.tb


class ExceptionTestCases(TestCase): #BaseTestCase):

    def test_resolveException(self):
        exception = RuntimeError('genric exception')
        twisted_failure = Failure(exception)
        out = resolveException(twisted_failure)
        self.assertIs(out, exception)

    def test_resolveException_with_exception_string(self):
        '''LEGASY: twisted.python.Failure requires a valid exception
        '''
        failure = DummyFailure()
        failure.type = "Products.ZenUtils.Exceptions.ZenPathError"
        out = resolveException(failure)
        expected = ZenPathError(failure.value, failure.tb)
        self.assertIsInstance(out, ZenPathError)
        self.assertEqual(out.args, expected.args)
        self.assertEqual(out.message, expected.message)

    def test_resolveException_with_exception_string_with_import_error(self):
        '''LEGASY: twisted.python.Failure requires a valid exception                                 
        '''
        failure = DummyFailure()
        failure.value = "value"
        failure.tb = "tb"
        failure.type = "Products.ZenUtils.Exceptions.UnknownError"
        out = resolveException(failure)
        expected = ZenResolveExceptionError(
            failure.value, failure.tb, failure.__dict__
        )
        self.assertIsInstance(out, Exception)
        self.assertEquals(out.args, ("value", "tb", failure.__dict__))

    def test_resolveException_with_raiseException(self):
        failure = DummyFailure()
        failure.raise_value = RuntimeError()
        self.assertIs(failure.raise_value, resolveException(failure))

    def test_resolveException_handles_twisted_spread_pb_RemoteError(self):
        error = RemoteError('remoteType', 'value', 'remoteTraceback')
        failure = Failure(error)
        #failure.type = 'twisted.spread.pb.RemoteError'
        out = resolveException(failure)
        self.assertEqual(out, error)

    def test_resolveException_provides_usefull_exception_for_unknown(self):
        failure = DummyFailure()
        failure.type = 'some.unknown.exception'
        out = resolveException(failure)
        expected = ZenResolveExceptionError(
            failure.value, failure.tb, failure.__dict__
        )
        self.assertIsInstance(out, ZenResolveExceptionError)
        self.assertEqual(out.args, expected.args)



def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(ExceptionTestCases))
    return suite
