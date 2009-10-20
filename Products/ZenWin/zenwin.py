#! /usr/bin/env python
# -*- coding: utf-8 -*-
# ##########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2006-2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
# ##########################################################################

"""
This module provides a collector daemon that polls Windows devices for changes
to Windows services. Retrieved status is then converted into Zenoss events
and sent back to ZenHub for further processing.
"""

import logging

# IMPORTANT! The import of the pysamba.twisted.reactor module should come before
# any other libraries that might possibly use twisted. This will ensure that
# the proper WmiReactor is installed before anyone else grabs a reference to
# the wrong reactor.
import pysamba.twisted.reactor

import Globals
import zope.component
import zope.interface

from twisted.internet import defer, reactor
from twisted.python.failure import Failure

from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import ICollectorPreferences,\
                                             IEventService,\
                                             IScheduledTask
from Products.ZenCollector.tasks import SimpleTaskFactory,\
                                        SimpleTaskSplitter,\
                                        TaskStates
from Products.ZenEvents.ZenEventClasses import Error, Clear, Status_WinService
from Products.ZenUtils.observable import ObservableMixin
from Products.ZenWin.WMIClient import WMIClient
from Products.ZenWin.Watcher import Watcher
from Products.ZenWin.utils import addNTLMv2Option, setNTLMv2Auth

# We retrieve our configuration data remotely via a Twisted PerspectiveBroker
# connection. To do so, we need to import the class that will be used by the
# configuration service to send the data over, i.e. DeviceProxy.
from Products.ZenUtils.Utils import unused
from Products.ZenCollector.services.config import DeviceProxy
unused(DeviceProxy)

#
# creating a logging context for this module to use
#
log = logging.getLogger("zen.zenwin")

# Create an implementation of the ICollectorPreferences interface so that the
# ZenCollector framework can configure itself from our preferences.
class ZenWinPreferences(object):
    zope.interface.implements(ICollectorPreferences)
    
    def __init__(self):
        """
        Construct a new ZenWinPreferences instance and provide default
        values for needed attributes.
        """
        self.collectorName = "zenwin"
        self.defaultRRDCreateCommand = None
        self.cycleInterval = 5 * 60 # seconds
        self.configCycleInterval = 20 # minutes
        self.options = None
        
        # the configurationService attribute is the fully qualified class-name
        # of our configuration service that runs within ZenHub
        self.configurationService = 'Products.ZenWin.services.WinServiceConfig'
        
        self.wmibatchSize = 10
        self.wmiqueryTimeout = 1000
        
    def buildOptions(self, parser):
        parser.add_option('--debug', dest='debug', default=False,
                               action='store_true',
                               help='Increase logging verbosity.')
        parser.add_option('--proxywmi', dest='proxywmi',
                               default=False, action='store_true',
                               help='Use a process proxy to avoid long-term blocking'
                               )
        parser.add_option('--queryTimeout', dest='queryTimeout',
                               default=None, type='int',
                               help='The number of milliseconds to wait for ' + \
                                    'WMI query to respond. Overrides the ' + \
                                    'server settings.')
        parser.add_option('--batchSize', dest='batchSize',
                               default=None, type='int',
                               help='Number of data objects to retrieve in a ' +
                                    'single WMI query.')
        addNTLMv2Option(parser)

    def postStartup(self):
        # turn on low-level pysamba debug logging if requested
        logseverity = self.options.logseverity
        if logseverity <= 5:
            pysamba.library.DEBUGLEVEL.value = 99

        # force NTLMv2 authentication if requested
        setNTLMv2Auth(self.options)


class ZenWinTask(ObservableMixin):
    zope.interface.implements(IScheduledTask)
        
    STATE_WMIC_CONNECT = 'WMIC_CONNECT'
    STATE_WMIC_QUERY = 'WMIC_QUERY'
    STATE_WMIC_PROCESS = 'WMIC_PROCESS'
    STATE_WATCHER_CONNECT = 'WATCHER_CONNECT'
    STATE_WATCHER_QUERY = 'WATCHER_QUERY'
    STATE_WATCHER_PROCESS = 'WATCHER_PROCESS'
    
    # windows service states from wmi queries (lowercased)
    RUNNING = "running"
    STOPPED = "stopped"
    
    def __init__(self,
                 deviceId,
                 taskName,
                 scheduleIntervalSeconds,
                 taskConfig):
        """
        Construct a new task instance to watch for Windows Event Log changes
        for the specified device.
        
        @param deviceId: the Zenoss deviceId to watch
        @type deviceId: string
        @param taskName: the unique identifier for this task
        @type taskName: string
        @param scheduleIntervalSeconds: the interval at which this task will be
               collected
        @type scheduleIntervalSeconds: int
        @param taskConfig: the configuration for this task
        """
        super(ZenWinTask, self).__init__()
        
        self.name = taskName
        self.configId = deviceId
        self.interval = scheduleIntervalSeconds
        self.state = TaskStates.STATE_IDLE
        
        self._taskConfig = taskConfig
        self._devId = deviceId
        self._manageIp = self._taskConfig.manageIp
        
        self._eventService = zope.component.queryUtility(IEventService)
        self._preferences = zope.component.queryUtility(ICollectorPreferences,
                                                        "zenwin")
                                                        
        # if the user hasn't specified the batchSize or queryTimeout as command
        # options then use whatever has been specified in the collector
        # preferences
        # TODO: convert these to zProperties
        self._batchSize = self._preferences.options.batchSize
        if not self._batchSize:
            self._batchSize = self._preferences.wmibatchSize
        self._queryTimeout = self._preferences.options.queryTimeout
        if not self._queryTimeout:
            self._queryTimeout = self._preferences.wmiqueryTimeout
            
        self._wmic = None # the WMIClient
        self._watcher = None
        self._reset()
        
    def _reset(self):
        """
        Reset the WMI client and notification query watcher connection to the
        device, if they are presently active.
        """
        if self._wmic:
            self._wmic.close()
        self._wmic = None
        if self._watcher:
            self._watcher.close()
        self._watcher = None
        
    def _finished(self, result):
        """
        Callback activated when the task is complete so that final statistics
        on the collection can be displayed.
        """
        if not isinstance(result, Failure):
            log.debug("Device %s [%s] scanned successfully",
                      self._devId, self._manageIp)
        else:
            log.debug("Device %s [%s] scanned failed, %s",
                      self._devId, self._manageIp, result.getErrorMessage())

        # give the result to the rest of the callback/errchain so that the
        # ZenCollector framework can keep track of the success/failure rate
        return result

    def _failure(self, result):
        """
        Errback for an unsuccessful asynchronous connection or collection 
        request.
        """
        err = result.getErrorMessage()
        log.error("Unable to scan device %s: %s", self._devId, err)

        self._reset()

        summary = """
            Could not read Windows services (%s). Check your
            username/password settings and verify network connectivity.
            """ % err

        self._eventService.sendEvent(dict(
            summary=summary,
            component='zenwin',
            eventClass=Status_WinService,
            device=self._devId,
            severity=Error,
            agent='zenwin',
            ))

        # give the result to the rest of the errback chain
        return result
        
    def _sendWinServiceEvent(self, name, summary, severity):
        event = {'summary': summary,
                 'eventClass': Status_WinService,
                 'device': self._devId,
                 'severity': severity,
                 'agent': 'zenwin',
                 'component': name,
                 'eventGroup': 'StatusTest'}
        self._eventService.sendEvent(event)
            
    def _handleResult(self, name, state):
        """
        Handle a result from the wmi query. Results from both the initial WMI
        client query and the watcher's notification query are processed by
        this method. Log running and stopped transitions. Send an event if the
        service is monitored.
        """
        state = state.lower()
        summary = "Windows service '%s' is %s" % (name, state)
        logLevel = logging.DEBUG
        if name in self._taskConfig.services:
            eventCount, stoppedSeverity = self._taskConfig.services[name]
            if state == self.RUNNING:
                self._sendWinServiceEvent(name, summary, Clear)
                logLevel = logging.INFO
                self._taskConfig.services[name] = (0, stoppedSeverity)
            elif state == self.STOPPED:
                self._sendWinServiceEvent(name, summary, stoppedSeverity)
                logLevel = logging.CRITICAL
                self._taskConfig.services[name] = (eventCount + 1, stoppedSeverity)
        log.log(logLevel, '%s on %s', summary, self._devId)
        
    def _collectSuccessful(self, results):
        """
        Callback for a successful fetch of services from the remote device.
        """
        self.state = ZenWinTask.STATE_WATCHER_PROCESS
        
        log.debug("Successful collection from %s [%s], results=%s",
                  self._devId, self._manageIp, results)
                  
        # make a local copy of monitored services list
        services = self._taskConfig.services.copy()
        if results:
            for result in [r.targetInstance for r in results]:
                if result.state:
                    if result.name in services:
                        # remove service from local copy
                        del services[result.name]
                    self._handleResult(result.name, result.state)
        # send events for the services that did not show up in results
        for name, (eventCount, stoppedSeverity) in services.items():
            if eventCount == 0:
                state = self.RUNNING
            else:
                state = self.STOPPED
            self._handleResult(name, state)
        if results:
            # schedule another immediate collection so that we'll keep eating
            # events as long as they are ready for us; using callLater ensures
            # it goes to the end of the immediate work-queue so that other 
            # events get processing time
            log.debug("Queuing another fetch for %s [%s]",
                      self._devId, self._manageIp)
            d = defer.Deferred()
            reactor.callLater(0, d.callback, None)
            d.addCallback(self._collectCallback)
            return d

    def _collectCallback(self, result):
        """
        Callback called after a connect or previous collection so that another
        collection can take place.
        """
        log.debug("Polling for events from %s [%s]", 
                  self._devId, self._manageIp)

        self.state = ZenWinTask.STATE_WATCHER_QUERY
        d = self._watcher.getEvents(self._queryTimeout, self._batchSize)
        d.addCallbacks(self._collectSuccessful, self._failure)
        return d

    def _connectCallback(self, result):
        """
        Callback called after a successful connect to the remote Windows device.
        """
        log.debug("Connected to %s [%s]", self._devId, self._manageIp)
        
    def _connectWatcher(self, result):
        self.state = ZenWinTask.STATE_WMIC_PROCESS
        for service in result['query']:
            self._handleResult(service.name, service.state)
        self._wmic.close()
        self._wmic = None
        self.state = ZenWinTask.STATE_WATCHER_CONNECT
        wql = "SELECT * FROM __InstanceModificationEvent WITHIN 5 "\
              "WHERE TargetInstance ISA 'Win32_Service'"
        self._watcher = Watcher(self._taskConfig, wql)
        return self._watcher.connect()
        
    def _initialQuery(self, result):
        self.state = ZenWinTask.STATE_WMIC_QUERY
        wql = "SELECT Name, State FROM Win32_Service"
        d = self._wmic.query({'query': wql})
        d.addCallback(self._connectWatcher)
        return d
        
    def _connect(self):
        """
        Called when a connection needs to be created to the remote Windows
        device.
        """
        log.debug("Connecting to %s [%s]", self._devId, self._manageIp)
        self.state = ZenWinTask.STATE_WMIC_CONNECT
        self._wmic = WMIClient(self._taskConfig)
        d = self._wmic.connect()
        d.addCallback(self._initialQuery)
        return d

    def cleanup(self):
        return self._reset()

    def doTask(self):
        log.debug("Scanning device %s [%s]", self._devId, self._manageIp)
        
        # see if we need to connect first before doing any collection
        if not self._watcher:
            d = self._connect()
            d.addCallbacks(self._connectCallback, self._failure)
        else:
            # since we don't need to bother connecting, we'll just create an 
            # empty deferred and have it run immediately so the collect callback
            # will be fired off
            d = defer.Deferred()
            reactor.callLater(0, d.callback, None)

        # try collecting events after a successful connect, or if we're already
        # connected
        d.addCallback(self._collectCallback)

        # Add the _finished callback to be called in both success and error
        # scenarios. While we don't need final error processing in this task,
        # it is good practice to catch any final errors for diagnostic purposes.
        d.addBoth(self._finished)

        # returning a Deferred will keep the framework from assuming the task
        # is done until the Deferred actually completes
        return d
    

#
# Collector Daemon Main entry point
#
if __name__ == '__main__':
    myPreferences = ZenWinPreferences()
    myTaskFactory = SimpleTaskFactory(ZenWinTask)
    myTaskSplitter = SimpleTaskSplitter(myTaskFactory)
    daemon = CollectorDaemon(myPreferences, myTaskSplitter)
    daemon.run()
