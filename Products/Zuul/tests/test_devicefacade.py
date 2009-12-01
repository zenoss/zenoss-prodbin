###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import unittest

import zope.component
from zope.interface.verify import verifyClass

from Products.Zuul.tests.base import ZuulFacadeTestCase
from Products.Zuul.interfaces import ISerializableFactory

from Products.Zuul.interfaces import IDeviceFacade

from Products.Zuul.interfaces import IDeviceInfo
from Products.Zuul.facades.devicefacade import DeviceInfo


class DeviceFacadeTest(ZuulFacadeTestCase):

    def setUp(self):
        super(ProcessFacadeTest, self).setUp()
        self.facade = zope.component.queryUtility(IDeviceFacade)

    def test_interfaces(self):
        verifyClass(IDeviceInfo, DeviceInfo)


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(DeviceFacadeTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
    
