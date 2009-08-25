###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import Globals
import zope.interface

from Products.ZenCollector.interfaces import ICollector, IScheduledTask
from Products.ZenCollector.tasks import SimpleTaskSplitter, SimpleTaskFactory
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.observable import ObservableMixin


class DummyObject(object):
    pass

class BasicTestTask(ObservableMixin):
    zope.interface.implements(IScheduledTask)

    def __init__(self, name, configId, interval, config):
        self.name = name
        self.configId = configId
        self.interval = interval
        self.config = config

    def doTask(self):
        pass


class TestSplitter(BaseTestCase):

    def testName(self):
        configs = []
        c = DummyObject()
        c.id = 'host1'
        c.configCycleInterval = 30
        configs.append(c)

        c = DummyObject()
        c.id = 'host2'
        c.configCycleInterval = 100
        configs.append(c)

        taskFactory = SimpleTaskFactory(BasicTestTask)
        taskSplitter = SimpleTaskSplitter(taskFactory)
        tasks = taskSplitter.splitConfiguration(configs)
        self.assertEquals(len(tasks), 2)

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestSplitter))
    return suite
