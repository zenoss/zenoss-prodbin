###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
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
