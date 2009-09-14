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

import logging

import zope.interface

from Products.ZenCollector.interfaces import IScheduledTaskFactory,\
                                             ITaskSplitter


#
# creating a logging context for this module to use
#
log = logging.getLogger("zen.collector.tasks")


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

    def splitConfiguration(self, configs):
        tasks = {}
        for config in configs:
            log.debug("splitting config %r", config)

            configId = config.id
            taskCycleInterval = config.configCycleInterval

            self._taskFactory.reset()
            self._taskFactory.name = configId
            self._taskFactory.configId = configId
            self._taskFactory.interval = taskCycleInterval
            self._taskFactory.config = config
            task = self._taskFactory.build()

            tasks[configId] = task
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
    STATE_PAUSED = 'PAUSED'
    STATE_CLEANING = 'CLEANING'
