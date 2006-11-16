import unittest
from glob import glob

from testgen.mechunit import MechanizeUnitTest

from Products import ZenTestUI

def test_suite():
    basePath = ZenTestUI.__path__[0]
    suites = []
    for filename in glob('%s/tests/TestGen4Web/*.xml' % basePath):
        loader = unittest.TestLoader()
        test = MechanizeUnitTest
        test.sourceFilename = filename
        suite = loader.loadTestsFromTestCase(test)
        suite = unittest.TestSuite(suite)
        suites.append(suite)
    return unittest.TestSuite(suites)

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())
