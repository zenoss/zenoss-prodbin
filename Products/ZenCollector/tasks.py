###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, 2010 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging
log = logging.getLogger("zen.collector.tasks")
from copy import copy
import random

import zope.interface

from Products.ZenCollector.interfaces import IScheduledTaskFactory,\
                                             ITaskSplitter, ISubTaskSplitter
from Products.ZenUtils.observable import ObservableMixin
from Products.ZenUtils.Utils import readable_time


class BaseTask(ObservableMixin):
    """
    Convenience class that consolidates some shared code.
    """

    def __init__(self, *args, **kwargs):
        super(BaseTask, self).__init__()

        # Store the original cycle interval so that we
        # can go back when an error condition is resolved.
        interval = kwargs.get('scheduleIntervalSeconds')
        if interval is not None:
            self._originalScheduleInterval = interval
        else:
            self._originalScheduleInterval = args[2]

    def cleanup(self): # Required by interface
        pass

    def _delayNextCheck(self):
        """
        Rather than keep re-polling at the same periodicity to
        determine if the device's agent is responding or not,
        let this task back up in the queue.
        Add a random element to it so that we don't get the
        thundering herd effect.
        A maximum delay is used so that there is a bound on the
        length of times between checks.
        """
        # If it's not responding, don't poll it so often
        if self.interval != self._maxbackoffseconds:
            delay = random.randint(int(self.interval / 2), self.interval) * 2
            self.interval = min(self._maxbackoffseconds, self.interval + delay)
            log.debug("Delaying next check for another %s",
                      readable_time(self.interval))

    def _returnToNormalSchedule(self, ignored=None):
        """
        Once a task is successful, reset the original cycle interval.
        The ignored kwarg is used so that the method can be called
        directly as a deferred callback.
        """
        if self.interval != self._originalScheduleInterval:
            self.interval = self._originalScheduleInterval
            log.debug("Resetting next check back to %s seconds",
                      self._originalScheduleInterval)

    def chunk(self, lst, n):
        """
        Break lst into n-sized chunks
        """
        return [lst[i:i+n] for i in range(0, len(lst), n)]


class NullTaskSplitter(object):
    """
    A task splitter that is used with a NullConfigService for
    situations where no configuration will be returned.
    """
    zope.interface.implements(ITaskSplitter)

    def splitConfiguration(self, configs):
        return {}


class SimpleTaskSplitter(object):
    """
    A task splitter that creates a single scheduled task for an entire 
    configuration.
    """
    zope.interface.implements(ITaskSplitter)

    def __init__(self, taskFactory):
        """
        Creates a new instance of DeviceTaskSpliter.

        @param taskClass the class to use when creating new tasks
        @type any Python class
        """
        if not IScheduledTaskFactory.providedBy(taskFactory):
            raise TypeError("taskFactory must implement IScheduledTaskFactory")
        else:
            self._taskFactory = taskFactory

    def _newTask(self, name, configId, interval, config):
        """
        Handle the dirty work of creating a task
        """
        self._taskFactory.reset()
        self._taskFactory.name = name
        self._taskFactory.configId = configId
        self._taskFactory.interval = interval
        self._taskFactory.config = config

        return self._taskFactory.build()

    def splitConfiguration(self, configs):
        tasks = {}
        for config in configs:
            log.debug("splitting config %r", config)

            configId = config.id
            interval = config.configCycleInterval
            tasks[configId] = self._newTask(configId, configId,
                                            interval, config)
        return tasks


class SubConfigurationTaskSplitter(SimpleTaskSplitter):
    """
    A task splitter that creates a single scheduled task by
    device, cycletime and other criteria.
    """
    zope.interface.implements(ISubTaskSplitter)
    subconfigName = 'datasources'

    def makeConfigKey(self, config, subconfig):
        raise NotImplementedError("Required method not implemented")

    def _splitSubConfiguration(self, config):
        subconfigs = {}
        for subconfig in getattr(config, self.subconfigName):
            key = self.makeConfigKey(config, subconfig)
            subconfigList = subconfigs.setdefault(key, [])
            subconfigList.append(subconfig)
        return subconfigs

    def splitConfiguration(self, configs):
        # This name required by ITaskSplitter interface
        tasks = {}
        for config in configs:
            log.debug("Splitting config %s", config)

            # Group all of the subtasks under the same configId
            # so that updates clean up any previous tasks
            # (including renames)
            configId = config.id

            subconfigs = self._splitSubConfiguration(config)
            for key, subconfigGroup in subconfigs.items():
                name = ' '.join(map(str, key))
                interval = key[1]

                configCopy = copy(config)
                setattr(configCopy, self.subconfigName, subconfigGroup)

                tasks[name] = self._newTask(name,
                                            configId,
                                            interval,
                                            configCopy)
        return tasks


class SimpleTaskFactory(object):
    """
    A simple task factory that creates a scheduled task using the provided
    task class and the minimum attributes needed for a task.
    """
    zope.interface.implements(IScheduledTaskFactory)

    def __init__(self, taskClass):
        """
        Create a new task factory instance using the specified task class when
        creating new task objects. The taskClass must provide an __init__ method
        with the following signature:
        
        def __init__(self, name, configId, interval, config):
        
        @param taskClass: the class to use when creating new task objects
        @type taskClass: a Python class object
        """
        self._taskClass = taskClass
        self.reset()

    def build(self):
        return self._taskClass(self.name,
                               self.configId,
                               self.interval,
                               self.config)

    def reset(self):
        self.name = None
        self.configId = None
        self.interval = None
        self.config = None


class TaskStates(object):
    STATE_IDLE = 'IDLE'
    STATE_RUNNING = 'RUNNING'
    STATE_WAITING = 'WAITING'
    STATE_QUEUED = 'QUEUED'
    STATE_PAUSED = 'PAUSED'
    STATE_CLEANING = 'CLEANING'
    STATE_COMPLETED = 'COMPLETED'
