import unittest
from zope.testing import doctest

optionflags = doctest.REPORT_ONLY_FIRST_FAILURE | doctest.ELLIPSIS

def test_suite():
    from zope.testing.doctestunit import DocTestSuite
    suite = DocTestSuite('Products.ZenModel.version.Version')
    return unittest.TestSuite((suite),)
