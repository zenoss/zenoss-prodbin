#!/usr/bin/env python

from Products.ZenUtils.Exceptions import resolveException, ZentinelException, ZenPathError
from Products.ZenTestCase.BaseTestCase import BaseTestCase

class Failure(object):
    def __init__(self):
        self.value = None
        self.type = None
        self.tb = None
        self.raise_value = None

    def raiseException(self):
        raise self.raise_value, self.type, self.tb

class ExceptionTestCases(BaseTestCase):
    def test_resolveException_with_exception_value(self):
        failure = Failure()
        failure.value = ZentinelException()
        self.assertIs( failure.value, resolveException( failure))

    def test_resolveException_with_exception_string(self):
        failure = Failure()
        failure.type = "Products.ZenUtils.Exceptions.ZenPathError"
        self.assertIsInstance( resolveException( failure), ZenPathError)

    def test_resolveException_with_exception_string_with_import_error(self):
        failure = Failure()
        failure.value = "value"
        failure.tb = "tb"
        failure.type = "Products.ZenUtils.Exceptions.UnknownError"
        actual = resolveException( failure)
        self.assertIsInstance( actual, Exception)
        self.assertEquals( ("value", "tb"), actual.args)

    def test_resolveException_with_raiseException(self):
        failure = Failure()
        failure.raise_value = RuntimeError()
        self.assertIs( failure.raise_value, resolveException( failure))

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(ExceptionTestCases))
    return suite
