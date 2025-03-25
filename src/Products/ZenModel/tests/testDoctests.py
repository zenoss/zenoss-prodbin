##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

from types import ModuleType

from Products import ZenModel as TARGET_MODULE
from Products.ZenUtils.ZenDocTest import ZenDocTestRunner
from Products.ZenUtils.ZenDocTest import TestSuiteWithHooks


def get_submodules(mod):
    vals = mod.__dict__.values()
    allmods = filter(lambda x: type(x) is ModuleType, vals)
    return filter(lambda x: x.__name__.startswith(mod.__name__), allmods)


def test_suite():
    suite = TestSuiteWithHooks()
    zdtr = ZenDocTestRunner()
    suite.setUp, suite.tearDown = zdtr.setUp, zdtr.tearDown
    modules = get_submodules(TARGET_MODULE)
    zdtr.add_modules(modules)
    for dtsuite in zdtr.get_suites():
        suite.addTest(dtsuite)
    return suite
