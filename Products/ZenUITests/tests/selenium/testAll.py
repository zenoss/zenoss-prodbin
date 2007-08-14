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
import smtplib

from util.selTestUtils import replaceChar

def findTest(str):
    """Returns module names from filenames of the form "TestSomething.py" """
    exp = re.compile("^Test\w+\.py$")
    match = exp.match(str)
    if match is not None:
        return match.group()[:-3] # Strip off the ".py" to get module name
    else:
        return None

loader = unittest.TestLoader()
runner = unittest.TextTestRunner(verbosity = 0) # Enables detailed output.

subDirs = os.walk('.') # Recursively get subdirectories and their contents.
testTargets = []

for dir in subDirs:
    rootDir = dir[0]
    fileList = dir[2]
    
    for file in fileList:
        modName = findTest(file)
        if modName is not None:
            modName = ((rootDir + '/')[2:] + modName).replace('/', '.')
            testTargets.append(modName)

# The following lines will run all tests in the current directory only.
# directoryContents = os.listdir(".") # must be run within the test directory
# List comprehension of all test module names, according to findTest
# testTargets = [findTest(x) for x in directoryContents if findTest(x) is not None]

testAll = loader.loadTestsFromNames(testTargets) # Load test modules
                                     
result = runner.run(testAll)