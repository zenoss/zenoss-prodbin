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

import Globals
import zope.interface

from twisted.internet import defer, reactor

from Products.ZenCollector.interfaces import IScheduledTask
from Products.ZenCollector.scheduler import CallableTask, Scheduler, TaskStates
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.observable import ObservableMixin

class BasicTestTask(ObservableMixin):
    zope.interface.implements(IScheduledTask)

    def __init__(self):
        super(BasicTestTask, self).__init__()
        self.name = "BasicTestTask"
        self.interval = 60
        self.state = "IDLE"
        self.missedRuns = 0
        self.totalRuns = 0

    def doTask(self):
        pass

class TestScheduler(BaseTestCase):
    def testDeleteTasks(self):
        myTask1 = BasicTestTask()
        myTask1.name = "myDevice:myTask1"
        myTask1.configId = "myDevice"

        myTask2 = BasicTestTask()
        myTask2.name = "myDevice:myTask2"
        myTask2.configId = "myDevice"

        myTask3 = BasicTestTask()
        myTask3.name = "myDevice2:myTask3"
        myTask3.configId = "myDevice2"

        scheduler = Scheduler()
        scheduler.addTask(myTask1)
        scheduler.addTask(myTask2)
        scheduler.addTask(myTask3)
        self.assertEquals(len(scheduler._tasks), 3)
        self.assertTrue(scheduler._tasks.has_key(myTask1.name))
        self.assertTrue(scheduler._tasks.has_key(myTask2.name))
        self.assertTrue(scheduler._tasks.has_key(myTask3.name))

        scheduler.removeTasksForConfig("myDevice")
        self.assertEquals(len(scheduler._tasks), 1)
        self.assertTrue(scheduler._tasks.has_key(myTask3.name))

    def testTaskDoneCallback(self):
        myTask1 = BasicTestTask()
        myTask1.name = "myTask1"
        myTask1.configId = "myTask1"

        called = False
        def myCallback(taskName):
            self.assertEquals(taskName, myTask1.name)
            called = True

        scheduler = Scheduler()
        scheduler.addTask(myTask1, myCallback)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestScheduler))
    return suite
