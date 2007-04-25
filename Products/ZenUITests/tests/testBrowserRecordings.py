###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
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
    #import pdb; pdb.set_trace()
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

