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
import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from types import ModuleType
from unittest import TestSuite

from Products import ZenModel
from Products.ZenUtils.ZenDocTest import ZenDocTestRunner

def get_submodules(mod):
    vals = ZenModel.__dict__.values()
    allmods = filter(lambda x:type(x)==ModuleType, vals)
    submods = filter(lambda x:x.__name__.startswith(mod.__name__), allmods)
    return submods

def test_suite():
    suite = TestSuite()
    dtr = ZenDocTestRunner()
    mods = get_submodules(ZenModel)
    dtr.add_modules(mods)
    for dtsuite in dtr.get_suites(): suite.addTest(dtsuite)
    return suite

if __name__=="__main__":
    framework()
