#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__ = '''suite.py

A script for running a suite of tests stored in a file

$Version: $'''

__version__ = "$Revision: 1.1 $"[11:-2]

import unittest
import sys

filename = "test-suite"
if len(sys.argv) == 2:
    filename = sys.argv[1]

modules = open(filename).readlines()

suite = unittest.TestSuite()
for module in modules:
    module = module.rstrip()
    className=module.split('.')[-1]
    module = ".".join(module.split('.')[:-1])
    print "Module",module
    print "Class",className
    mod = __import__(module, globals(), locals(), className)
    suite.addTest(
        unittest.makeSuite(getattr(mod, className), 'test'))
unittest.TextTestRunner().run(suite)
