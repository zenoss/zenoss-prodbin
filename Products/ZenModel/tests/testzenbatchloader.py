###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import os
import os.path
import logging

from DateTime import DateTime
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenModel.BatchDeviceLoader import BatchDeviceLoader

class FakeConfigs: pass

class FakeOptions:
    def __init__(self):
        self.nocommit = True


class Testzenbatchloader(BaseTestCase):

    def afterSetUp(self):
        super(Testzenbatchloader, self).afterSetUp()

        self.zloader = BatchDeviceLoader(noopts=1)
        self.zloader.options = FakeOptions()
        self.zloader.options.nomodel = True
        self.zloader.options.nocommit = False

        self.log = logging.getLogger("zen.BatchDeviceLoader")
        self.zloader.log = self.log

    def testSampleConfig(self):
        """
        Is the internal sample config still working?
        """
        configs = self.zloader.sample_configs.split('\n')
        device_list = self.zloader.parseDevices(configs)
        self.zloader.processDevices(device_list)

    def testCProps(self):
        """
        Verify that we can set custom properties
        """
        olympics = DateTime("2010/02/28")
        configs = ["device1 cDateTest=%s" % repr(olympics)]
        device_list = self.zloader.parseDevices(configs)
        self.zloader.processDevices(device_list)

        dev = self.zloader.dmd.Devices.findDevice('device1')
        self.assert_(dev.cDateTest == olympics)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(Testzenbatchloader))
    return suite

