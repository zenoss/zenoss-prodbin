###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import os, sys

if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from types import ModuleType


from Products.ZenUtils.ZenDocTest import ZenDocTestRunner
from Products.ZenUtils.ZenDocTest import TestSuiteWithHooks

from Products.ZenRRD.parsers import uptime

DOCTEST_MODULES = [uptime]

def test_suite():
    suite = TestSuiteWithHooks()
    zdtr = ZenDocTestRunner()
    suite.setUp, suite.tearDown = zdtr.setUp, zdtr.tearDown
    zdtr.add_modules(DOCTEST_MODULES)
    for dtsuite in zdtr.get_suites():
        suite.addTest(dtsuite)
    return suite

if __name__=="__main__":
    if None: framework = None
    framework()
