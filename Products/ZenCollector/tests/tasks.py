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

from Products.ZenCollector.interfaces import ICollector
from Products.ZenCollector.tasks import CollectorTask, DeviceTaskSplitter
from Products.ZenTestCase.BaseTestCase import BaseTestCase


class DummyObject(object):
    pass


class DummyCollector(object):
    zope.interface.implements(ICollector)
    pass


class BasicTestTask(CollectorTask):
    def doTask(self):
        pass


class Test(BaseTestCase):


    def testName(self):
        configs = []
        c = DummyObject()
        c.config = {'devId':'host1', 'manageIp': '127.0.0.1', 
                    'cycleSeconds':'30'}
        configs.append(c)
        
        c = DummyObject()
        c.config = {'devId':'host2', 'manageIp':'127.0.0.2',
                    'cycleSeconds':'180'}
        configs.append(c)

        taskSplitter = DeviceTaskSplitter(DummyCollector(), BasicTestTask)
        tasks = taskSplitter.splitConfiguration(configs)
        self.assertEquals(len(tasks), 2)

