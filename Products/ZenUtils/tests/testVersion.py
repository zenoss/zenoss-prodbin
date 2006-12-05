'''
Note that this is meant to be run from zopecctl using the "test" option. If you
would like to run these tests from python, simply to the following:

    python ZenUtils/Version.py
'''
import unittest
from zope.testing.doctestunit import DocTestSuite

def test_suite():
    suite = DocTestSuite('Products.ZenUtils.Version')
    return unittest.TestSuite([suite])

if __name__ == '__main__':
    print __doc__
