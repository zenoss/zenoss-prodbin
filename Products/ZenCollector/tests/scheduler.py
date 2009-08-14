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

from Products.ZenCollector.interfaces import IScheduledTask
from Products.ZenCollector.scheduler import CallableTask,\
                                            ScheduledTask,\
                                            Scheduler
from Products.ZenTestCase.BaseTestCase import BaseTestCase

class BasicTestTask(object):
    zope.interface.implements(IScheduledTask)

    def __init__(self):
        self.name = "BasicTestTask"
        self.interval = 0
        self.state = "IDLE"
        self.missedRuns = 0
        self.totalRuns = 0

    def doTask(self):
        pass


class Test(BaseTestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass


    def testCallableTaskException(self):
        # create a simple task that just throws an exception inside of doTask
        class MyTask(BasicTestTask):
            def doTask(self):
                raise IOError("this should not kill the framework")

        task = MyTask()
        CallableTask(task)()
        self.assertEquals(task.totalRuns, 1)


    def testTaskNotIdle(self):
        """
        Test that a task that is not in an IDLE state will not actually run and
        increments the missedRuns statistics.
        """
        class MyTask(BasicTestTask):
            def __init__(self):
                super(MyTask, self).__init__()
                self.state = "a non-idle state..."

            def doTask(self):
                raise Exception("this should never be executed")

        task = MyTask()
        CallableTask(task)()
        self.assertEquals(task.missedRuns, 1)


    def testTaskStateNormal(self):
        tester = self

        # make sure the task is in the RUNNING state when it's started
        class MyTask(BasicTestTask):
            def doTask(self):
                tester.assertTrue(self.state == ScheduledTask.STATE_RUNNING)

        myTask = MyTask()
        CallableTask(myTask)()

        # make sure the state returns to IDLE after a successful run
        self.assertTrue(myTask.state == ScheduledTask.STATE_IDLE)


    def testTaskStateFailure(self):
        tester = self

        # make sure the task is in the RUNNING state when it's started
        class MyTask(BasicTestTask):
            def doTask(self):
                tester.assertTrue(self.state == ScheduledTask.STATE_RUNNING)
                raise ValueError("pretending that something bad happened!")

        myTask = MyTask()
        CallableTask(myTask)()

        # make sure the state returns to IDLE after a failed run
        self.assertTrue(myTask.state == ScheduledTask.STATE_IDLE)


    def testDeleteTasks(self):
        myTask1 = BasicTestTask()
        myTask1.name = "myDevice:myTask1"
        myTask1.deviceId = "myDevice"

        myTask2 = BasicTestTask()
        myTask2.name = "myDevice:myTask2"
        myTask2.deviceId = "myDevice"
        
        myTask3 = BasicTestTask()
        myTask3.name = "myDevice2:myTask3"
        myTask3.deviceId = "myDevice2"

        scheduler = Scheduler()
        scheduler.addTask(myTask1)
        scheduler.addTask(myTask2)
        scheduler.addTask(myTask3)
        self.assertEquals(len(scheduler._tasks), 3)
        self.assertTrue(scheduler._tasks.has_key(myTask1.name))
        self.assertTrue(scheduler._tasks.has_key(myTask2.name))
        self.assertTrue(scheduler._tasks.has_key(myTask3.name))

        scheduler.removeTasksForDevice("myDevice")
        self.assertEquals(len(scheduler._tasks), 1)
        self.assertTrue(scheduler._tasks.has_key(myTask3.name))


    def testTaskDoneCallback(self):
        myTask1 = BasicTestTask()
        myTask1.name = "myTask1"
        mytask1.configId = "myTask1"

        called = False
        def myCallback(taskName):
            self.assertEquals(taskName, myTask1.name)
            called = True

        scheduler = Scheduler()
        scheduler.addTask(myTask1, myCallback)

        self.assertTrue(called)

