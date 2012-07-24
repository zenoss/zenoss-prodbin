##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import unittest
import warnings
from zope.testing.doctestunit import DocTestSuite


def test_suite():
    warnings.filterwarnings( 'ignore' )
    suite = DocTestSuite('Products.ZenUtils.Utils')
    jsonsuite = DocTestSuite('Products.ZenUtils.jsonutils')
    iputilsuite = DocTestSuite('Products.ZenUtils.IpUtil')
    skinssuite = DocTestSuite('Products.ZenUtils.Skins')
    return unittest.TestSuite([suite, jsonsuite, iputilsuite, skinssuite])
