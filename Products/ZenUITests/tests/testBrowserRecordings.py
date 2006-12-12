import unittest
from glob import glob

from testgen.mechunit import MechanizeUnitTest

def convertFilesToSuite(filenames):
    suites = []
    for filename in filenames:
        if not filename.endswith('testDevicesCreateDelete.xml'): continue
        loader = unittest.TestLoader()
        test = MechanizeUnitTest
        test.sf = filename
        suite = loader.loadTestsFromTestCase(test)
        suite = unittest.TestSuite([suite])
        suites.append(suite)
    return unittest.TestSuite(suites)

def test_suite():
    from Products import ZenUITests
    basePath = ZenUITests.__path__[0]
    filenames = glob('%s/tests/TestGen4Web/*.xml' % basePath)
    return convertFilesToSuite(filenames)

def nonZopeSuite():
    filenames = glob('tests/TestGen4Web/*.xml')
    filenames += glob('TestGen4Web/*.xml')
    return convertFilesToSuite(filenames)

if __name__ == '__main__':
    unittest.TextTestRunner().run(nonZopeSuite())
