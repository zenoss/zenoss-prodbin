#!/usr/bin/python
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

#
# Contained below is a convenience file for calling all tests.
#
# Adam Modlin and Nate Avers
#

import unittest
import re
import os


def findTest(str):
    """Returns module names from filenames of the form "TestSomething.py" """
    exp = re.compile("^Test\w+\.py$")
    match = exp.match(str)
    if match is not None:
        return match.group()[:-3] # Strip off the ".py" to get module name
    else:
        return None

loader = unittest.TestLoader()
runner = unittest.TextTestRunner(verbosity = 2) # Enables detailed output.

directoryContents = os.listdir(".") # must be run within the test directory
# List comprehension of all test module names, according to findTest
testTargets = [findTest(x) for x in directoryContents if findTest(x) is not None]

testAll = loader.loadTestsFromNames(testTargets)
                                     
result = runner.run(testAll)