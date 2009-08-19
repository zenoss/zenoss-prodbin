#############################################################################
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#############################################################################

import zope.component, zope.interface

from Products.ZenCollector import CoreCollectorFrameworkFactory
from Products.ZenCollector.interfaces import IFrameworkFactory
from Products.ZenTestCase.BaseTestCase import BaseTestCase

from Products.ZenCollector.config import ConfigurationProxy
from Products.ZenCollector.scheduler import Scheduler

class TestFactory(BaseTestCase):
    def testFactoryInstall(self):
        """
        Test to ensure the core factory returns the objects it should.
        """
        factory = CoreCollectorFrameworkFactory()

        configProxy = factory.getConfigurationProxy()
        self.assertTrue(isinstance(configProxy, ConfigurationProxy))

        scheduler = factory.getScheduler()
        self.assertTrue(isinstance(scheduler, Scheduler))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestFactory))
    return suite
