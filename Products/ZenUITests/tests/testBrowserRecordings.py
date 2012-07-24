##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import unittest
from glob import glob

from testgen.mechunit import MechanizeUnitTest

def convertFilesToSuite(filenames):
    suites = []
    for filename in filenames:
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
    filenames = [f for f in filenames if not f.split('/')[-1].startswith('ignore-')]
    return convertFilesToSuite(filenames)

def nonZopeSuite():
    filenames = glob('tests/TestGen4Web/*.xml')
    filenames += glob('TestGen4Web/*.xml')
    return convertFilesToSuite(filenames)

if __name__ == '__main__':
    unittest.TextTestRunner().run(nonZopeSuite())
