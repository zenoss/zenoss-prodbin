##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, 2010, 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
from twisted.internet import defer
from Products.ZenEvents.ZenEventClasses import Cmd_Fail, Error
import zope.component

log = logging.getLogger("zen.collector.tasks")
from copy import copy
import random

import zope.interface

from Products.ZenCollector.interfaces import IScheduledTaskFactory, ITaskSplitter, ISubTaskSplitter,\
                                             IScheduledTask, ICollectorWorker, ICollector, IWorkerExecutor
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
    
    def scheduled(self, scheduler): # Required by interface
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
        return ignored

    def chunk(self, lst, n):
        """
        Break lst into n-sized chunks
        """
        return [lst[i:i+n] for i in xrange(0, len(lst), n)]


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

            configId = config.configId
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
            configId = config.configId

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


class RRDWriter(object):
    def __init__(self, delegate):
        self.delegate = delegate

    def writeRRD(self, counter, countervalue, countertype, **kwargs):
        """
        write given data to RRD streaming files
        """
        self.delegate.writeRRD(counter, countervalue, countertype, **kwargs)

class EventSender(object):
    def __init__(self, delegate):
        self.delegate = delegate

    def sendEvent(self, event, **eventData):
        evt = event.copy()
        evt.update(eventData)
        self.delegate.sendEvent(evt)

class WorkerOutputProxy(object):
    def __init__(self, daemon=None, rrdWriter=None, eventSender=None):
        self.daemon = daemon
        self.rrdWriter = rrdWriter if not daemon else RRDWriter(daemon)
        self.eventSender = eventSender if not daemon else EventSender(daemon)

    @defer.inlineCallbacks
    def sendOutput(self, data, events, intervalSeconds):
        if self.rrdWriter:
            for d in data:
                yield self.rrdWriter.writeRRD(d['path'],
                                d['value'],
                                d['rrdType'],
                                rrdCommand=d['rrdCommand'],
                                cycleTime=intervalSeconds,
                                min=d['min'],
                                max=d['max']
                )

        if self.eventSender:
            for ev in events:
                self.sendEvent(ev)

    @defer.inlineCallbacks
    def sendEvent(self, event):
        yield self.eventSender.sendEvent(event)

class SingleWorkerTask(ObservableMixin):
    zope.interface.implements(IScheduledTask)

    def __init__(self,
                 deviceId,
                 taskName,
                 scheduleIntervalSeconds,
                 taskConfig):
        """
        Construct a new task instance to fetch data from the configured worker object

        @param deviceId: the Zenoss deviceId to watch
        @type deviceId: string
        @param taskName: the unique identifier for this task
        @type taskName: string
        @param scheduleIntervalSeconds: the interval at which this task will be
               collected
        @type scheduleIntervalSeconds: int
        @param taskConfig: the configuration for this task
        """
        super(SingleWorkerTask, self).__init__()

        self.name = taskName
        self.configId = deviceId
        self.interval = scheduleIntervalSeconds
        self.state = TaskStates.STATE_IDLE

        self._taskConfig = taskConfig
        self._devId = deviceId
        self._manageIp = self._taskConfig.manageIp
        self._worker = None

        self.daemon = zope.component.getUtility(ICollector)
        self.outputProxy = WorkerOutputProxy(self.daemon)
        self.component = self.daemon.preferences.collectorName

        options = self.daemon.options
        taskOptionDict = dict((attr, value) for (attr, value) in options.__dict__.items()
            if value is not None and not attr.startswith('_') and not callable(value))
        self._taskConfig.options = taskOptionDict


    @property
    def deviceId(self):
        return self._devId

    @property
    def worker(self):
        """
        Instance of the worker class to use for all tasks
        """
        return self._worker
    @worker.setter
    def worker(self, value):
        self._worker = value

    @defer.inlineCallbacks
    def cleanup(self):
        """
        Delegate cleanup directly to the worker object
        """
        try:
            self.state = TaskStates.STATE_CLEANING
            if self.worker:
                yield self.worker.stop()
        finally:
            self.state = TaskStates.STATE_COMPLETED

    @defer.inlineCallbacks
    def doTask(self):
        """
        Delegate collection directly work to the worker object
        """
        results = None
        try:
            self.state = TaskStates.STATE_RUNNING
            if self.worker:
                # perform data collection in the worker object
                results = yield self.worker.collect(self._devId, self._taskConfig)

        except Exception as ex:
            log.error("worker collection: results (exception) = %r (%s)", results, ex)
            collectionErrorEvent = {'device':self.deviceId, 'severity':Error, 'eventClass':Cmd_Fail,
                                    'summary':'Exception collecting:'+str(ex),
                                    'component':self.component, 'agent':self.component}
            yield self.outputProxy.sendEvent(collectionErrorEvent)

        else:
            if results:
                #send the data through the output proxy
                data, events = results
                if 'testcounter' in self._taskConfig.options:
                    testCounter = self._taskConfig.options['testcounter']
                    for dp in data:
                        if dp['counter'] == testCounter:
                            log.info("Collected value for %s: %s (%s)", dp['counter'], dp['value'], dp['path'])
                            break
                    else:
                        log.info("No value collected for %s from device %s", testCounter, self._devId)
                        log.debug("Valid counters: %s", [dp['counter'] for dp in data])

                yield self.outputProxy.sendOutput(data, events, self.interval)

        finally:
            self.state = TaskStates.STATE_IDLE

class SingleWorkerTaskFactory(SimpleTaskFactory):
    """
    A task factory that creates a scheduled task using the provided
    task class and the minimum attributes needed for a task, plus redirects
    the 'doTask' and 'cleanup' methods to a single ICollectorWorker instance.
    """
    zope.interface.implements(IScheduledTaskFactory)

    def __init__(self, taskClass=SingleWorkerTask, iCollectorWorker=None):
        super(SingleWorkerTaskFactory, self).__init__(taskClass)
        self.workerClass = iCollectorWorker

    def setWorkerClass(self, iCollectorWorker):
        self.workerClass = iCollectorWorker

    def postInitialization(self):
        pass
    
    def build(self):
        task = super(SingleWorkerTaskFactory, self).build()
        if self.workerClass and ICollectorWorker.implementedBy(self.workerClass):
            worker = self.workerClass()
            worker.prepareToRun()
            task.worker = worker
        return task

class NullWorkerExecutor(object):
    """
    IWorkerExecutor that does nothing with the provided worker
    """
    zope.interface.implements(IWorkerExecutor)

    def setWorkerClass(self, workerClass):
        pass

    def run(self):
        pass


class TaskStates(object):
    STATE_IDLE = 'IDLE'
    STATE_RUNNING = 'RUNNING'
    STATE_WAITING = 'WAITING'
    STATE_QUEUED = 'QUEUED'
    STATE_PAUSED = 'PAUSED'
    STATE_CLEANING = 'CLEANING'
    STATE_COMPLETED = 'COMPLETED'
    STATE_SHUTDOWN = "SHUTDOWN"
