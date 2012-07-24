#!/usr/bin/env python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


#
# Contained below is a convenience file for calling all tests.
#
# Adam Modlin and Nate Avers
#

import unittest
import re
import os
import sys

HERE = os.path.abspath(os.path.dirname(__file__))

TESTFMT     = re.compile("^Test\w+\.py$")

def findTest(str):
    """Returns module names from filenames of the form "TestSomething.py" """
    match = TESTFMT.match(str)
    if match is not None:
        return match.group()[:-3] # Strip off the ".py" to get module name
    else:
        return None

testout = sys.stdout
loader = unittest.TestLoader()
runner = unittest.TextTestRunner(stream = testout,  verbosity = 2) # Enables detailed output.

testTargets = []

for root, subDirs, files in os.walk(HERE):
        for file in files:
            modName = findTest(file)
            if modName is not None:
                testTargets.append(modName)

print testTargets
testAll = loader.loadTestsFromNames(testTargets) # Load test modules
result = runner.run(testAll)
