##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import random
from Products.ZenUtils.Executor import TwistedExecutor

"""
Support for scheduling tasks and running them on a periodic interval. Tasks
are associated directly with a device, but multiple tasks may exist for a
single device or other monitored object.
"""

import logging
import math
import signal
import time
from StringIO import StringIO

import zope.interface

from twisted.internet import defer, reactor, task
from twisted.python.failure import Failure

from Products.ZenCollector.interfaces import IScheduler, IScheduledTask
from Products.ZenCollector.tasks import TaskStates
from Products.ZenUtils.Utils import dumpCallbacks

#
# creating a logging context for this module to use
#
log = logging.getLogger("zen.collector.scheduler")


class StateStatistics(object):
    def __init__(self, state):
        self.state = state
        self.reset()

    def addCall(self, elapsedTime):
        self.totalElapsedTime += elapsedTime
        self.totalElapsedTimeSquared += elapsedTime ** 2
        self.totalCalls += 1

        if self.totalCalls == 1:
            self.minElapsedTime = elapsedTime
            self.maxElapsedTime = elapsedTime
        else:
            self.minElapsedTime = min(self.minElapsedTime, elapsedTime)
            self.maxElapsedTime = max(self.maxElapsedTime, elapsedTime)

    def reset(self):
        self.totalElapsedTime = 0.0
        self.totalElapsedTimeSquared = 0.0
        self.totalCalls = 0
        self.minElapsedTime = 0xffffffff
        self.maxElapsedTime = 0

    @property
    def mean(self):
        return float(self.totalElapsedTime) / float(self.totalCalls)

    @property
    def stddev(self):
        if self.totalCalls == 1:
            return 0
        else:
            # see http://www.dspguide.com/ch2/2.htm for stddev of running stats
            return math.sqrt((self.totalElapsedTimeSquared - self.totalElapsedTime ** 2 / self.totalCalls) / (self.totalCalls - 1))


class TaskStatistics(object):
    def __init__(self, task):
        self.task = task
        self.totalRuns = 0
        self.failedRuns = 0
        self.missedRuns = 0
        self.states = {}
        self.stateStartTime = None

    def trackStateChange(self, oldState, newState):
        now = time.time()

        # record how long we spent in the previous state, if there was one
        if oldState is not None and self.stateStartTime:
            # TODO: how do we properly handle clockdrift or when the clock
            # changes, or is time.time() independent of that?
            elapsedTime = now - self.stateStartTime
            previousState = newState

            if oldState in self.states:
                stats = self.states[oldState]
            else:
                stats = StateStatistics(oldState)
                self.states[oldState] = stats
            stats.addCall(elapsedTime)

        self.stateStartTime = now


class CallableTask(object):
    """
    A CallableTask wraps an object providing IScheduledTask so that it can be
    treated as a callable object. This allows the scheduler to make use of the
    Twisted framework's LoopingCall construct for simple interval-based
    scheduling.
    """
    def __init__(self, task, scheduler, executor):
        if not IScheduledTask.providedBy(task):
            raise TypeError("task must provide IScheduledTask")
        else:
            self.task = task

        self._scheduler = scheduler
        self._executor = executor
        self.paused = False
        self.taskStats = None

    def __repr__(self):
        return "CallableTask: %s" % getattr(self.task, 'name', self.task)

    def running(self):
        """
        Called whenever this task is being run.
        """
        self.taskStats.totalRuns += 1

    def logTwistedTraceback(self, reason):
        """
        Twisted errBack to record a traceback and log messages
        """
        out = StringIO()
        reason.printTraceback(out)
        # This shouldn't be necessary except for dev code
        log.debug(out.getvalue())
        out.close()

    def finished(self, result):
        """
        Called whenever this task has finished.
        """
        if isinstance(result, Failure):
            self.taskStats.failedRuns += 1
            self.logTwistedTraceback(result)

    def late(self):
        """
        Called whenever this task is late and missed its scheduled run time.
        """
        # TODO: report an event
        self.taskStats.missedRuns += 1


    def __call__(self):
        if self.task.state is TaskStates.STATE_PAUSED and not self.paused:
            self.task.state = TaskStates.STATE_IDLE

        if self.task.state is TaskStates.STATE_IDLE:
            if self.paused:
                self.task.state = TaskStates.STATE_PAUSED
            else:
                self.task.state = TaskStates.STATE_QUEUED
                # don't return deferred to looping call.
                # If a deferred is returned to looping call
                # it won't reschedule on error and will only
                # reschedule after the deferred is done. This method
                # should be called regardless of whether or
                # not the task is still running to keep track
                # of "late" tasks
                d = self._executor.submit(self._doCall)
                def _callError(failure):
                    msg = "%s - %s failed %s" % (self.task, self.task.name,
                                                   failure)
                    log.debug(msg)
                    # don't return failure to prevent
                    # "Unhandled error in Deferred" message
                    return msg
                #l last error handler in the chain
                d.addErrback(_callError)
        else:
            self._late()
        # don't return a Deferred because we want LoopingCall to keep
        # rescheduling so that we can keep track of late intervals

    def _doCall(self):
        d = defer.maybeDeferred(self._run)
        d.addBoth(self._finished)

        # dump the deferred chain if we're in ludicrous debug mode
        if log.getEffectiveLevel() < logging.DEBUG:
            print "Callback Chain for Task %s" % self.task.name
            dumpCallbacks(d)
        return d

    def _run(self):
        self.task.state = TaskStates.STATE_RUNNING
        self.running()
        return self.task.doTask()

    def _finished(self, result):
        log.debug("Task %s finished, result: %r", self.task.name,
                  result)

        # Unless the task completed or paused itself, make sure
        # that we always reset the state to IDLE once the task is finished.
        if self.task.state != TaskStates.STATE_COMPLETED:
            self.task.state = TaskStates.STATE_IDLE

        self._scheduler.taskDone(self.task.name)

        self.finished(result)

        if self.task.state == TaskStates.STATE_COMPLETED:
            self._scheduler.removeTasksForConfig(self.task.configId)

        # return result for executor callbacks
        return result

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
        return CallableTask(newTask, scheduler, scheduler.executor)


class Scheduler(object):
    """
    A simple interval-based scheduler that makes use of the Twisted framework's
    LoopingCall construct.
    """

    zope.interface.implements(IScheduler)

    CLEANUP_TASKS_INTERVAL = 10 # seconds

    def __init__(self, callableTaskFactory=CallableTaskFactory()):
        self._loopingCalls = {}
        self._tasks = {}
        self._taskCallback = {}
        self._taskStats = {}
        self._callableTaskFactory = callableTaskFactory
        self._shuttingDown = False
        # create a cleanup task that will periodically sweep the
        # cleanup dictionary for tasks that need to be cleaned
        self._tasksToCleanup = set()
        self._cleanupTask = task.LoopingCall(self._cleanupTasks)
        self._cleanupTask.start(Scheduler.CLEANUP_TASKS_INTERVAL)

        self._executor = TwistedExecutor(1)

        # Ensure that we can cleanly shutdown all of our tasks
        reactor.addSystemEventTrigger('before', 'shutdown', self.shutdown, 'before')
        reactor.addSystemEventTrigger('during', 'shutdown', self.shutdown, 'during')
        reactor.addSystemEventTrigger('after', 'shutdown', self.shutdown, 'after')

    def __contains__(self, task):
        """
        Returns True if the task has been added to the scheduler.  Otherwise
        False is returned.
        """
        # If task has no 'name' attribute, assume the task name was passed in.
        name = getattr(task, "name", task)
        return name in self._tasks

    def shutdown(self, phase):
        """
        The reactor shutdown has three phases for event types:

               before - tasks can shut down safely at this time with access to all
                        services (eg EventService, their own services)
               during - EventService and other services are gone before this starts
               after  - not a lot left -- be careful

        Tasks that have the attribute 'stopPhase' can set the state for which
        they should be run, otherwise they will be shut down in the 'before' phase.

        Tasks that have the attribute 'stopOrder' can set the order in which they
        are shut down (lowest first).  A stopOrder of 0 (zero) is assumed for tasks
        which do not declare a stopOrder.

        Returns a list of deferreds to wait on.
        """
        self._shuttingDown = True
        doomedTasks = []
        stopQ = {}
        log.debug("In shutdown stage %s", phase)
        for (taskName, taskWrapper) in self._tasks.iteritems():
            task = taskWrapper.task
            stopPhase = getattr(task, 'stopPhase', 'before')
            if stopPhase in ('before', 'after', 'during') and \
               stopPhase != phase:
                continue
            stopOrder = getattr(task, 'stopOrder', 0)
            queue = stopQ.setdefault(stopOrder, [])
            queue.append( (taskName, taskWrapper, task) )

        for stopOrder in sorted(stopQ):
            for (taskName, taskWrapper, task) in stopQ[stopOrder]:
                loopTask = self._loopingCalls[taskName]
                if loopTask.running:
                    log.debug("Stopping running task %s", taskName)
                    loopTask.stop()
                log.debug("Removing task %s", taskName)
                doomedTasks.append(taskName)
                self.taskRemoved(taskWrapper)

        for taskName in doomedTasks:
            self._tasksToCleanup.add(self._tasks[taskName].task)

            del self._loopingCalls[taskName]
            del self._tasks[taskName]
            del self._taskStats[taskName]

        cleanupList = self._cleanupTasks()
        return defer.DeferredList(cleanupList)

    @property
    def executor(self):
        return self._executor

    def _getMaxTasks(self):
        return self._executor.getMax()

    def _setMaxTasks(self, max):
        return self._executor.setMax(max)

    maxTasks = property(_getMaxTasks, _setMaxTasks)

    def _ltCallback(self, result, task_name):
        """last call back in the chain, if it gets called as an errBack
        the looping will stop - shouldn't be called since CallableTask
        doesn't return a deferred, here for sanity and debug"""
        if task_name in self._loopingCalls:
            loopingCall = self._loopingCalls[task_name]
            log.debug("call finished %s : %s" %(loopingCall, result))
        if isinstance(result, Failure):
            log.warn("Failure in looping call, will not reschedule %s" % task_name)
            log.error("%s" % result)

    def _startTask(self, result, task_name, interval):
        """start the task using a callback so that its put at the bottom of
        the Twisted event queue, to allow other processing to continue and
        to support a task start-time jitter"""
        if task_name in self._loopingCalls:
            loopingCall = self._loopingCalls[task_name]
            if not loopingCall.running:
                log.debug("Task %s starting on %d second intervals", task_name, interval)
                d = loopingCall.start(interval)
                d.addBoth(self._ltCallback, task_name)

    def addTask(self, newTask, callback=None, now=False):
        """
        Add a new IScheduledTask to the scheduler for execution.
        @param newTask the new task to schedule
        @type newTask IScheduledTask
        @param callback a callback to be notified each time the task completes
        @type callback a Python callable
        """
        if newTask.name in self._tasks:
            raise ValueError("Task %s already exists" % newTask.name)
        log.debug("add task %s, %s using %s second interval", newTask.name, newTask, newTask.interval)
        callableTask = self._callableTaskFactory.getCallableTask(newTask, self)
        loopingCall = task.LoopingCall(callableTask)
        self._loopingCalls[newTask.name] = loopingCall
        self._tasks[newTask.name] = callableTask
        self._taskCallback[newTask.name] = callback
        self.taskAdded(callableTask)
        d = defer.Deferred()
        d.addCallback(self._startTask, newTask.name, newTask.interval)

        startDelay = getattr(newTask, 'startDelay', None)
        if startDelay is None:
            startDelay = 0 if now else self._getStartDelay(newTask)
        # explicitly set, next expected call in case task was never executed/schedule
        loopingCall._expectNextCallAt = time.time() + startDelay
        reactor.callLater(startDelay, d.callback, None)

        # just in case someone does not implement scheduled, lets be careful
        scheduled = getattr(newTask, 'scheduled', lambda x: None)
        scheduled(self)

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
        task = taskWrapper.task

        # watch the task's attribute changes
        task.attachAttributeObserver('state', self._taskStateChangeListener)
        task.attachAttributeObserver('interval', self._taskIntervalChangeListener)

        # create the statistics data for this task
        self._taskStats[task.name] = TaskStatistics(task)
        taskWrapper.taskStats = self._taskStats[task.name]

    def taskRemoved(self, taskWrapper):
        """
        Called whenever the scheduler removes a task.
        """
        task = taskWrapper.task
        task.detachAttributeObserver('state', self._taskStateChangeListener)
        task.detachAttributeObserver('interval', self._taskIntervalChangeListener)

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

    def getTasksForConfig(self, configId):
        """
        Get all tasks associated with the specified identifier.
        """
        tasks = []
        for (taskName, taskWrapper) in self._tasks.iteritems():
            task = taskWrapper.task
            if task.configId == configId:
                tasks.append(task)
        return tasks

    def getNextExpectedRun(self, taskName):
        """
        Get the next expected execution time for given task
        """
        loopingCall = self._loopingCalls.get(taskName, None)
        if loopingCall:
            return loopingCall._expectNextCallAt

    def removeTasks(self, taskNames):
        """
        Remove tasks
        """
        doomedTasks = []
        # child ids are any task that are children of the current task being
        # removed
        childIds = []
        for taskName in taskNames:
            taskWrapper = self._tasks[taskName]
            task = taskWrapper.task
            subIds = getattr(task, "childIds", None)
            if subIds:
                childIds.extend(subIds)
            log.debug("Stopping task %s, %s", taskName, task)
            if self._loopingCalls[taskName].running:
                self._loopingCalls[taskName].stop()

            doomedTasks.append(taskName)
            self.taskRemoved(taskWrapper)

        for taskName in doomedTasks:
            task = self._tasks[taskName].task
            self._tasksToCleanup.add(task)
            del self._loopingCalls[taskName]
            del self._tasks[taskName]
            self._displayTaskStatistics(task)
            del self._taskStats[taskName]
            # TODO: ponder task statistics and keeping them around?

        map(self.removeTasksForConfig, childIds)

        # TODO: don't let any tasks for the same config start until
        # these old tasks are really gone

    def removeTasksForConfig(self, configId):
        """
        Remove all tasks associated with the specified identifier.

        @paramater configId: the identifier to search for
        @type configId: string
        """
        self.removeTasks(taskName for taskName, taskWrapper in self._tasks.iteritems() if taskWrapper.task.configId == configId)

    def pauseTasksForConfig(self, configId):
        for (taskName, taskWrapper) in self._tasks.items():
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

    def _taskStateChangeListener(self, observable, attrName, oldValue, newValue):
        task = observable

        log.debug("Task %s changing state from %s to %s", task.name, oldValue,
                  newValue)

        taskStat = self._taskStats[task.name]
        taskStat.trackStateChange(oldValue, newValue)

    def _taskIntervalChangeListener(self, observable, attrName, oldValue, newValue):
        """
        Allows tasks to change their collection interval on the fly
        """
        task = observable
        log.debug("Task %s changing run interval from %s to %s", task.name, oldValue,
                  newValue)

        loopingCall = task._dataService._scheduler._loopingCalls[task.name]
        loopingCall.interval = newValue

    @property
    def missedRuns(self):
        totalMissedRuns = 0
        for taskWrapper in self._tasks.itervalues():
            task = taskWrapper.task
            taskStats = self._taskStats[task.name]
            totalMissedRuns += taskStats.missedRuns
        return totalMissedRuns

    @property
    def failedRuns(self):
        totalFailedRuns = 0
        for taskWrapper in self._tasks.itervalues():
            task = taskWrapper.task
            taskStats = self._taskStats[task.name]
            totalFailedRuns += taskStats.failedRuns
        return totalFailedRuns

    @property
    def taskCount(self):
        return len(self._tasks)

    def displayStatistics(self, verbose):
        totalRuns = 0
        totalFailedRuns = 0
        totalMissedRuns = 0
        totalTasks = 0
        stateStats = {}

        for taskWrapper in self._tasks.itervalues():
            task = taskWrapper.task
            taskStats = self._taskStats[task.name]

            totalTasks += 1
            totalRuns += taskStats.totalRuns
            totalFailedRuns += taskStats.failedRuns
            totalMissedRuns += taskStats.missedRuns

            for state, stats in taskStats.states.iteritems():
                if state in stateStats:
                    totalStateStats = stateStats[state]
                else:
                    totalStateStats = StateStatistics(state)
                    stateStats[state] = totalStateStats
                totalStateStats.totalElapsedTime += stats.totalElapsedTime
                totalStateStats.totalElapsedTimeSquared += stats.totalElapsedTimeSquared
                totalStateStats.totalCalls += stats.totalCalls
                totalStateStats.minElapsedTime = min(totalStateStats.minElapsedTime, stats.minElapsedTime)
                totalStateStats.maxElapsedTime = max(totalStateStats.maxElapsedTime, stats.maxElapsedTime)

        log.info("Tasks: %d Successful_Runs: %d Failed_Runs: %d Missed_Runs: %d " \
                 "Queued_Tasks: %d Running_Tasks: %d ",
                 totalTasks, totalRuns, totalFailedRuns, totalMissedRuns,
                 self.executor.queued, self.executor.running)

        if verbose:
            buffer = "Task States Summary:\n"
            buffer = self._displayStateStatistics(buffer, stateStats)

            buffer += "\nTasks:\n"
            for taskWrapper in self._tasks.itervalues():
                task = taskWrapper.task
                taskStats = self._taskStats[task.name]

                buffer += "%s Current State: %s Successful_Runs: %d Failed_Runs: %d Missed_Runs: %d\n" \
                    % (task.name, task.state, taskStats.totalRuns,
                       taskStats.failedRuns, taskStats.missedRuns)

            buffer += "\nDetailed Task States:\n"
            for taskWrapper in self._tasks.itervalues():
                task = taskWrapper.task
                taskStats = self._taskStats[task.name]

                if not taskStats.states: # Hasn't run yet
                    continue

                buffer = self._displayStateStatistics(buffer,
                                             taskStats.states,
                                             "%s " % task.name)

                if hasattr(task, 'displayStatistics'):
                    buffer += task.displayStatistics()

                buffer += "\n"

            log.info("Detailed Scheduler Statistics:\n%s", buffer)

        # TODO: the above logic doesn't print out any stats for the 'current'
        # state... i.e. enter the PAUSED state and wait there an hour, and
        # you'll see no data

        # TODO: should we reset the statistics here, or do it on a periodic
        # interval, like once an hour or day or something?

    def _displayTaskStatistics(self, task):
        verbose = log.isEnabledFor(logging.DEBUG)
        if not verbose:
            return
        taskStats = self._taskStats[task.name]

        buffer = "%s Current State: %s Successful_Runs: %d Failed_Runs: %d Missed_Runs: %d\n" \
            % (task.name, task.state, taskStats.totalRuns,
               taskStats.failedRuns, taskStats.missedRuns)

        buffer += "\nDetailed Task States:\n"
        if taskStats.states: # Hasn't run yet
            buffer = self._displayStateStatistics(buffer,
                                         taskStats.states,
                                         "%s " % task.name)

            if hasattr(task, 'displayStatistics'):
                buffer += task.displayStatistics()

        buffer += "\n"

        log.info("Detailed Task Statistics:\n%s", buffer)

    def _displayStateStatistics(self, buffer, stateStats, prefix=''):
        for state, stats in stateStats.iteritems():
            buffer += "%sState: %s Total: %d Total Elapsed: %.4f Min: %.4f Max: %.4f Mean: %.4f StdDev: %.4f\n" \
                % (prefix,
                   state, stats.totalCalls, stats.totalElapsedTime,
                   stats.minElapsedTime, stats.maxElapsedTime, stats.mean,
                   stats.stddev)
        return buffer

    def _cleanupTasks(self):
        """
        Periodically cleanup tasks that have been queued up for cleaning.
        """
        # Build a list of the tasks that need to be cleaned up so that there
        # is no issue with concurrent modifications to the _tasksToCleanup
        # dictionary when tasks are quickly cleaned up.
        if self._tasksToCleanup:
            log.debug("tasks to clean %s" % self._tasksToCleanup)

        todoList = [task for task in self._tasksToCleanup
                             if self._isTaskCleanable(task)]

        cleanupWaitList = []
        for task in todoList:
            # changing the state of the task will keep the next cleanup run
            # from processing it again
            task.state = TaskStates.STATE_CLEANING
            if self._shuttingDown:
                #let the task know the scheduler is shutting down
                task.state = TaskStates.STATE_SHUTDOWN
            log.debug("Cleanup on task %s %s", task.name, task)
            d = defer.maybeDeferred(task.cleanup)
            d.addBoth(self._cleanupTaskComplete, task)
            cleanupWaitList.append(d)
        return cleanupWaitList

    def _cleanupTaskComplete(self, result, task):
        """
        Twisted callback to remove a task from the cleanup queue once it has
        completed its cleanup work.
        """
        log.debug("Scheduler._cleanupTaskComplete: result=%s task.name=%s" % (result, task.name))
        self._tasksToCleanup.discard(task)
        return result

    def _isTaskCleanable(self, task):
        """
        Determines if a task is able to be cleaned up or not.
        """
        return task.state in (TaskStates.STATE_IDLE,
                              TaskStates.STATE_PAUSED,
                              TaskStates.STATE_COMPLETED)
