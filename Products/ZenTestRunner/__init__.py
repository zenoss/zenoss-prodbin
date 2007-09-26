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
import os
import unittest
from glob import glob

def getTestSuites(product):
    suites = []
    testDir = 'tests'
    path = os.path.join(product.__path__[0], testDir)
    testFiles = glob("%s/test*.py" % path)
    testMods = [ os.path.basename(x).split(os.path.extsep)[0]
        for x in testFiles ]
    for testMod in testMods:
        mod = __import__("%s.%s.%s" % (product.__name__, testDir, testMod),
            None, None, [''])
        suites.append(mod.test_suite())
    suite = unittest.TestSuite()
    suite.addTests(suites)
    return suite
