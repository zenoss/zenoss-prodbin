import unittest
from zope.testing import doctest

def test_suite():
    from zope.testing.doctestunit import DocTestSuite
    suite = DocTestSuite('Products.ZenModel.version.Version')
    return unittest.TestSuite((suite),)
