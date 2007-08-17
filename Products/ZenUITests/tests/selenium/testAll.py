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

######## BEGIN GLOBAL DEFS ########
MAILSERVER  = "%s" %sys.argv[1]
FROMADDR    = "testsuite@%s" %(sys.argv[1].split('.', 1)[1])
TOADDR      = "%s" %sys.argv[2]
SUBJECT     = "Selenium Test Suite Results - "
TESTFMT     = re.compile("^Test\w+\.py$")
######### END GLOBAL DEFS #########

def findTest(str):
    """Returns module names from filenames of the form "TestSomething.py" """
    match = TESTFMT.match(str)
    if match is not None:
        return match.group()[:-3] # Strip off the ".py" to get module name
    else:
        return None

loader = unittest.TestLoader()
runner = unittest.TextTestRunner(verbosity = 2) # Enables detailed output.

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

if len(result.errors) > 0 or len(result.failures) > 0:
    messageHeader = "From: %s\nTo: %s\nSubject: %s\n\n"\
                    %(FROMADDR, TOADDR, SUBJECT + "Problems Encountered")
else:
    messageHeader = "From: %s\nTo: %s\nSubject: %s\n\n"\
                    %(FROMADDR, TOADDR, SUBJECT + "All ok!")
messageBody = ""

for error in result.errors:
    messageBody += "%s: ERROR\n" %error[0].shortDescription()
    messageBody += '-'*75 + '\n'
    messageBody += error[1]
    messageBody += '-'*75 + '\n\n'

messageBody += "\n\n"

for failure in result.failures:
    messageBody += "%s: FAILURE" %failure[0].shortDescription()
    messageBody += '-'*75 + '\n'
    messageBody += failure[1] + '\n\n'
    messageBody += '-'*75 + '\n'

mailServer = smtplib.SMTP(MAILSERVER)
mailServer.sendmail(FROMADDR, TOADDR, messageHeader + messageBody)
mailServer.quit()
