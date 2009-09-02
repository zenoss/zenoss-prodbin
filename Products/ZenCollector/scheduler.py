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
import random

"""
Support for scheduling tasks and running them on a periodic interval. Tasks
are associated directly with a device, but multiple tasks may exist for a
single device or other monitored object.
"""

import logging

import zope.interface
from twisted.internet import defer, reactor, task

from Products.ZenCollector.interfaces import IScheduler, IScheduledTask
from Products.ZenCollector.tasks import TaskStates
from Products.ZenUtils.Utils import dumpCallbacks

#
# creating a logging context for this module to use
#
log = logging.getLogger("zen.collector.scheduler")


class CallableTask(object):
    """
    A CallableTask wraps an object providing IScheduledTask so that it can be
    treated as a callable object. This allows the scheduler to make use of the
    Twisted framework's LoopingCall construct for simple interval-based
    scheduling.
    """
    def __init__(self, task, scheduler):
        if not IScheduledTask.providedBy(task):
            raise TypeError("task must provide IScheduledTask")
        else:
            self.task = task

        self._scheduler = scheduler
        self.paused = False

    def running(self):
        """
        Called whenever this task is being run.
        """
        pass

    def finished(self, result):
        """
        Called whenever this task has finished.
        """
        pass

    def late(self):
        """
        Called whenever this task is late and missed its scheduled run time.
        """
        pass

    def __call__(self):
        if self.task.state is TaskStates.STATE_PAUSED and not self.paused:
            self.task.state = TaskStates.STATE_IDLE

        if self.task.state is TaskStates.STATE_IDLE:
            if self.paused:
                self.task.state = TaskStates.STATE_PAUSED
            else:
                d = defer.maybeDeferred(self._run)
                d.addBoth(self._finished)
                # don't return the Deferred because we want LoopingCall to keep
                # rescheduling so that we can keep track of late intervals

                # dump the deferred chain if we're in ludicrous debug mode
                if log.getEffectiveLevel() < logging.DEBUG:
                    print "Callback Chain for Task %s" % self.task.name
                    dumpCallbacks(d)

        else:
            self._late()

    def _run(self):
        self.task.state = TaskStates.STATE_RUNNING
        self.running()
        return self.task.doTask()

    def _finished(self, result):
        log.debug("Task %s finished, result: %r", self.task.name, 
                  result)

        # Make sure we always reset the state to IDLE once the task is
        # finished, regardless of what the outcome was.
        self.task.state = TaskStates.STATE_IDLE

        self._scheduler.taskDone(self.task.name)

        self.finished(result)
        # We handled any error; eat the result!

    def _late(self):
        log.debug("Task %s skipped because it was not idle", 
                  self.task.name)
        self.late()

class CallableTaskFactory(object):
    """
    A factory that creates instances of CallableTask, allowing it to be
    easily subclassed or replaced in different scheduler implementations.
    """
    def getCallableTask(self, newTask, scheduler):
        return CallableTask(newTask, scheduler)


class Scheduler(object):
    """
    A simple interval-based scheduler that makes use of the Twisted framework's
    LoopingCall construct.
    """

    zope.interface.implements(IScheduler)

    def __init__(self, callableTaskFactory=CallableTaskFactory()):
        self._loopingCalls = {}
        self._tasks = {}
        self._taskCallback = {}
        self._callableTaskFactory = callableTaskFactory

    def addTask(self, newTask, callback=None, now=False):
        """
        Add a new IScheduledTask to the scheduler for execution.
        @param newTask the new task to schedule
        @type newTask IScheduledTask
        @param callback a callback to be notified each time the task completes
        @type callback a Python callable
        """
        if self._tasks.has_key(newTask.name):
            raise ValueError("Task %s already exists" % newTask.name)

        callableTask = self._callableTaskFactory.getCallableTask(newTask, self)
        loopingCall = task.LoopingCall(callableTask)
        self._loopingCalls[newTask.name] = loopingCall
        self._tasks[newTask.name] = callableTask
        self._taskCallback[newTask.name] = callback
        self.taskAdded(callableTask)

        # start the task using a callback so that its put at the bottom of
        # the Twisted event queue, to allow other processing to continue and
        # to support a task start-time jitter
        def _startTask(result):
            log.debug("Task %s starting on %d second intervals",
                      newTask.name, newTask.interval)
            loopingCall.start(newTask.interval)
        d = defer.Deferred()
        d.addCallback(_startTask)
        startDelay = 0
        if not now:
            startDelay = self._getStartDelay(newTask)
        reactor.callLater(startDelay, d.callback, None)

    def _getStartDelay(self, task):
        """
        amount of time to delay the start of a task. Prevents bunching up of 
        task execution when a large amount of tasks are scheduled at the same 
        time.
        """
        #simple delay of random number between 0 and half the task interval
        delay = random.randint(0, int(task.interval/2))
        return delay
    
    def taskAdded(self, taskWrapper):
        """
        Called whenever the scheduler adds a task.
        """
        pass

    def taskRemoved(self, taskWrapper):
        """
        Called whenever the scheduler removes a task.
        """
        pass

    def taskPaused(self, taskWrapper):
        """
        Called whenever the scheduler pauses a task.
        """
        pass

    def taskResumed(self, taskWrapper):
        """
        Called whenever the scheduler resumes a task.
        """
        pass

    def removeTasksForConfig(self, configId):
        """
        Remove all tasks associated with the specified identifier.
        @param configId the identifier to search for
        @type configId string
        """
        doomedTasks = []
        for (taskName, taskWrapper) in self._tasks.iteritems():
            task = taskWrapper.task
            if task.configId == configId:
                log.debug("Stopping task %s", taskName)
                self._loopingCalls[taskName].stop()
                doomedTasks.append(taskName)
                self.taskRemoved(taskWrapper)

        for taskName in doomedTasks:
            del self._loopingCalls[taskName]
            del self._tasks[taskName]
            # TODO: ponder task statistics and keeping them around?

        # TODO: don't let any tasks for the same config start until
        # these old tasks are really gone

    def pauseTasksForConfig(self, configId):
        for (taskName, taskWrapper) in self._tasks.iteritems():
            task = taskWrapper.task
            if task.configId == configId:
                log.debug("Pausing task %s", taskName)
                taskWrapper.paused = True
                self.taskPaused(taskWrapper)

    def resumeTasksForConfig(self, configId):
        for (taskName, taskWrapper) in self._tasks.iteritems():
            task = taskWrapper.task
            if task.configId == configId:
                log.debug("Resuming task %s", taskName)
                taskWrapper.paused = False
                self.taskResumed(taskWrapper)

    def taskDone(self, taskName):
        if callable(self._taskCallback[taskName]):
            self._taskCallback[taskName](taskName=taskName)

    def displayStatistics(self, verbose=False):
        # no statistics in this scheduler
        pass
