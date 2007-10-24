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
import sys
import smtplib
import StringIO

TESTFMT     = re.compile("^Test\w+\.py$")

def findTest(str):
    """Returns module names from filenames of the form "TestSomething.py" """
    match = TESTFMT.match(str)
    if match is not None:
        return match.group()[:-3] # Strip off the ".py" to get module name
    else:
        return None

testout = StringIO.StringIO('')
loader = unittest.TestLoader()
runner = unittest.TextTestRunner(stream = testout,  verbosity = 2) # Enables detailed output.

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

testAll = loader.loadTestsFromNames(testTargets) # Load test modules
result = runner.run(testAll)

if len(result.errors) > 0 or len(result.failures) > 0:
    print testout.getvalue()
