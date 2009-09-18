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

import time

from DateTime import DateTime

from Acquisition import aq_base
from Products.ZenModel.Exceptions import *

from ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.IpService import IpService


class TestDeviceComponent(ZenModelBaseTest):

    def setUp(self):
        ZenModelBaseTest.setUp(self)
        self.dev = self.dmd.Devices.createInstance("testdev")
        tmpo = IpService('ipsvc')
        self.dev.os.ipservices._setObject('ipsvc',tmpo)
        tmpo.port = 121
        tmpo.protocol = 'tcp'
        self.ipsvc = self.dev.os.ipservices()[0]

        self.ipsvc.setServiceClass({'protocol':'tcp','port':121})
        self.sc = self.dmd.Services.IpService.serviceclasses.tcp_00121

    def test_setAqProperty(self):

        self.sc.zFailSeverity = 2

        self.ipsvc.setAqProperty('zFailSeverity', 2, 'int')
        self.assertEqual(self.ipsvc.hasProperty('zFailSeverity'), False)

        self.ipsvc.setAqProperty('zFailSeverity', 5, 'int')
        self.assertEqual(aq_base(self.ipsvc).zFailSeverity, 5)

        self.ipsvc.setAqProperty('zFailSeverity', 3, 'int')
        self.assertEqual(aq_base(self.ipsvc).zFailSeverity, 3)

        self.ipsvc.setAqProperty('zFailSeverity', 2, 'int')
        self.assertEqual(self.ipsvc.hasProperty('zFailSeverity'), False)



def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestDeviceComponent))
    return suite

if __name__=="__main__":
    framework()
