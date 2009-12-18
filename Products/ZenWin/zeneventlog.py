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
to the Windows Event Log. Retrieved events are then converted into Zenoss events
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
                                             IScheduledTask,\
                                             IStatisticsService
from Products.ZenCollector.tasks import SimpleTaskFactory,\
                                        SimpleTaskSplitter,\
                                        TaskStates
from Products.ZenEvents.ZenEventClasses import Clear, Error, Warning, Info, \
    Debug, Status_Wmi
from Products.ZenUtils.observable import ObservableMixin
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
log = logging.getLogger("zen.zeneventlog")


# Create an implementation of the ICollectorPreferences interface so that the
# ZenCollector framework can configure itself from our preferences.
class ZenEventLogPreferences(object):
    zope.interface.implements(ICollectorPreferences)

    def __init__(self):
        """
        Constructs a new ZenEventLogPreferences instance and provide default
        values for needed attributes.
        """
        self.collectorName = "zeneventlog"
        self.defaultRRDCreateCommand = None
        self.cycleInterval = 5 * 60 # seconds
        self.configCycleInterval = 20 # minutes
        self.options = None

        # the configurationService attribute is the fully qualified class-name
        # of our configuration service that runs within ZenHub
        self.configurationService = 'Products.ZenWin.services.EventLogConfig'

        self.wmibatchSize = 10
        self.wmiqueryTimeout = 1000

    def buildOptions(self, parser):
        parser.add_option('--batchSize', dest='batchSize',
                          default=None, type='int',
                          help='Number of data objects to retrieve in a ' +
                               'single WMI query.')

        parser.add_option('--queryTimeout', dest='queryTimeout',
                          default=None, type='int',
                          help='The number of milliseconds to wait for ' + \
                               'WMI query to respond. Overrides the ' + \
                               'server settings.')
        addNTLMv2Option(parser)

    def postStartup(self):
        # turn on low-level pysamba debug logging if requested
        logseverity = self.options.logseverity
        if logseverity <= 5:
            pysamba.library.DEBUGLEVEL.value = 99

        # force NTLMv2 authentication if requested
        setNTLMv2Auth(self.options)

        # add our collector's custom statistics
        statService = zope.component.queryUtility(IStatisticsService)
        statService.addStatistic("events", "COUNTER")

#
# Create an implementation of the IScheduledTask interface that will perform
# the actual collection work needed by this collector. In this case, we will
# scan Windows devices for changes to the Windows event log using a WMI
# notification query. These queries are open-ended queries that wait until data
# has been added to the WMI class specified in the query. This task will poll
# for any changed events with a small timeout period before returning to an 
# idle state and trying again at the next collection interval.
#
# TODO: this is a timing bug with this approach where we can lose events in the
# following scenarios:
#   1. Anytime the daemon is shutdown and restarted.
#   2. Anytime we reset our WMI connection and create a new one.
#
class ZenEventLogTask(ObservableMixin):
    """
    A scheduled task that watches the event log on a single Windows device.
    """
    zope.interface.implements(IScheduledTask)

    EVENT_LOG_NOTIFICATION_QUERY = """
        SELECT * FROM __InstanceCreationEvent
        WHERE TargetInstance ISA 'Win32_NTLogEvent'
          AND TargetInstance.EventType <= %d
        """

    STATE_CONNECTING = 'CONNECTING'
    STATE_POLLING = 'POLLING'
    STATE_PROCESSING = 'PROCESSING'

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
        super(ZenEventLogTask, self).__init__()

        self.name = taskName
        self.configId = deviceId
        self.interval = scheduleIntervalSeconds
        self.state = TaskStates.STATE_IDLE

        self._taskConfig = taskConfig
        self._devId = deviceId
        self._manageIp = self._taskConfig.manageIp

        # Create the actual query that will be used based upon the template and
        # the devices's  zWinEventlogMinSeverity zProperty. If this zProperty
        # changes then the task will be deleted and a new one created, so it
        # is okay to do so here in the constructor.
        self._wmiQuery = ZenEventLogTask.EVENT_LOG_NOTIFICATION_QUERY % \
            int(self._taskConfig.zWinEventlogMinSeverity)

        self._eventService = zope.component.queryUtility(IEventService)
        self._statService = zope.component.queryUtility(IStatisticsService)
        self._preferences = zope.component.queryUtility(ICollectorPreferences,
                                                        "zeneventlog")

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

        self._watcher = None
        self._reset()

    def _reset(self):
        """
        Reset the WMI notification query watcher connection to the device, if
        one is presently active.
        """
        if self._watcher:
            self._watcher.close()
        self._watcher = None

    def _makeEvent(self, lrec):
        """
        Put event in the queue to be sent to the ZenEventManager.
        
        @param lrec: log record
        @type lrec: log record object
        @return: dictionary with event keys and values
        @rtype: dictionary
        """
        lrec = lrec.targetinstance
        evtkey = '%s_%s' % (lrec.sourcename, lrec.eventcode)
        sev = Debug
        if lrec.eventtype == 1:
            sev = Error  # error
        elif lrec.eventtype == 2:
            sev = Warning  # warning
        elif lrec.eventtype in (3, 4, 5):
            sev = Info  # information, security audit success & failure

        log.debug( "---- log record info --------------" )
        for item in dir(lrec):
            if item[0] == '_':
                continue
            log.debug("%s = %s"  % (item, getattr(lrec, item, '')))
        log.debug( "---- log record info --------------" )

        ts= lrec.timegenerated
        try:
            date_ts = '/'.join( [ ts[0:4], ts[4:6], ts[6:8] ])
            time_ts = ':'.join( [ts[8:10], ts[10:12], ts[12:14] ])
            ts = date_ts + ' ' + time_ts
        except:
            pass

        event_message = str(lrec.message).strip()
        if not event_message or event_message == 'None':
            event_message = "Message text from Windows not available." + \
                            "  See source system's event log." 

        evt = dict(
            device=self._devId,
            eventClassKey=evtkey,
            eventGroup=lrec.logfile,
            component=lrec.sourcename,
            ntevid=lrec.eventcode,
            summary=event_message,
            agent='zeneventlog',
            severity=sev,
            monitor=self._preferences.options.monitor,
            user=lrec.user,
            categorystring=lrec.categorystring,
            originaltime=ts,
            computername=lrec.computername,
            eventidentifier=lrec.eventidentifier,
            )
        log.debug("Device:%s msg:'%s'", self._devId, lrec.message)
        return evt

    def _finished(self, result):
        """
        Callback activated when the task is complete so that final statistics
        on the collection can be displayed.
        """
        if not isinstance(result, Failure):
            log.debug("Device %s [%s] scanned successfully, %d events processed",
                      self._devId, self._manageIp, self._eventsFetched)
            stat = self._statService.getStatistic("events")
            stat.value += self._eventsFetched
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
            Could not read the Windows event log (%s). Check your
            username/password settings and verify network connectivity.
            """ % err

        self._eventService.sendEvent(dict(
            summary=summary,
            component='zeneventlog',
            eventClass=Status_Wmi,
            device=self._devId,
            severity=Error,
            agent='zeneventlog',
            ))

        # give the result to the rest of the errback chain
        return result

    def _collectSuccessful(self, result):
        """
        Callback for a successful fetch of events from the remote device.
        """
        self.state = ZenEventLogTask.STATE_PROCESSING

        log.debug("Successful collection from %s [%s], result=%s",
                  self._devId, self._manageIp, result)

        events = result
        if events:
            # process all of the fetched events
            for logRecord in events:
                self._eventsFetched += 1
                # TODO: figure out how to post this state on the cycle interval
                self._eventService.sendEvent(self._makeEvent(logRecord))

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

    def _deviceUp(self, result):
        msg = 'WMI connection to %s up.' % self._devId
        self._eventService.sendEvent(dict(
            summary=msg,
            eventClass=Status_Wmi,
            device=self._devId,
            severity=Clear,
            component='zeneventlog'))
        return result

    def _collectCallback(self, result):
        """
        Callback called after a connect or previous collection so that another
        collection can take place.
        """
        log.debug("Polling for events from %s [%s]", 
                  self._devId, self._manageIp)

        self.state = ZenEventLogTask.STATE_POLLING
        d = self._watcher.getEvents(self._queryTimeout, self._batchSize)
        d.addCallbacks(self._collectSuccessful, self._failure)
        d.addCallbacks(self._deviceUp)
        return d

    def _connectCallback(self, result):
        """
        Callback called after a successful connect to the remote Windows device.
        """
        log.debug("Connected to %s [%s]", self._devId, self._manageIp)

    def _connect(self):
        """
        Called when a connection needs to be created to the remote Windows
        device.
        """
        log.debug("Connecting to %s [%s]", self._devId, self._manageIp)

        self.state = ZenEventLogTask.STATE_CONNECTING
        self._watcher = Watcher(self._taskConfig, self._wmiQuery)
        return self._watcher.connect()

    def cleanup(self):
        return self._reset()

    def doTask(self):
        log.debug("Scanning device %s [%s]", self._devId, self._manageIp)

        self._eventsFetched = 0

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
    myPreferences = ZenEventLogPreferences()

    myTaskFactory = SimpleTaskFactory(ZenEventLogTask)
    myTaskSplitter = SimpleTaskSplitter(myTaskFactory)
    daemon = CollectorDaemon(myPreferences, myTaskSplitter)
    daemon.run()
