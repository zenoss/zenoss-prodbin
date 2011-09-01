#! /usr/bin/env python 
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2010 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""zenperfsnmp

Gets SNMP performance data and stores it in RRD files.

"""
import random
import logging
log = logging.getLogger("zen.zenperfsnmp")

import Globals
import zope.interface

from twisted.internet import defer, error
from twisted.python.failure import Failure
from pynetsnmp.twistedsnmp import AgentProxy, snmpprotocol, Snmpv3Error

from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import ICollectorPreferences,\
                                             IDataService,\
                                             IEventService,\
                                             IScheduledTask
from Products.ZenCollector.tasks import SimpleTaskFactory,\
                                        SimpleTaskSplitter,\
                                        TaskStates, \
                                        BaseTask
from Products.ZenUtils.Utils import importClass, readable_time
from Products.ZenUtils.Chain import Chain
from Products.ZenEvents.ZenEventClasses import Perf_Snmp, Status_Snmp, Status_Perf
from Products.ZenEvents import Event

# We retrieve our configuration data remotely via a Twisted PerspectiveBroker
# connection. To do so, we need to import the class that will be used by the
# configuration service to send the data over, i.e. SnmpDeviceProxy.
from Products.ZenUtils.Utils import unused
from Products.ZenHub.services.SnmpPerformanceConfig import SnmpDeviceProxy
unused(SnmpDeviceProxy)
from Products.ZenHub.services.PerformanceConfig import SnmpConnInfo
unused(SnmpConnInfo)

COLLECTOR_NAME = "zenperfsnmp"
MAX_BACK_OFF_MINUTES = 20


class SnmpPerformanceCollectionPreferences(object):
    zope.interface.implements(ICollectorPreferences)

    def __init__(self):
        """
        Constructs a new SnmpPerformanceCollectionPreferences instance and 
        provides default values for needed attributes.
        """
        self.collectorName = COLLECTOR_NAME
        self.defaultRRDCreateCommand = None
        self.configCycleInterval = 20 # minutes
        self.cycleInterval = 5 * 60 # seconds

        # The configurationService attribute is the fully qualified class-name
        # of our configuration service that runs within ZenHub
        self.configurationService = 'Products.ZenHub.services.SnmpPerformanceConfig'

        # Will be filled in based on buildOptions
        self.options = None

    def buildOptions(self, parser):
        parser.add_option('--showrawresults',
                          dest='showrawresults',
                          action="store_true",
                          default=False,
                          help="Show the raw RRD values. For debugging purposes only.")

        parser.add_option('--maxbackoffminutes',
                          dest='maxbackoffminutes',
                          default=MAX_BACK_OFF_MINUTES,
                          help="When a device fails to respond, increase the time to" \
                               " check on the device until this limit.")

    def postStartup(self):
        pass


class SingleOidSwitchException(Exception):
    pass

STATUS_EVENT = { 'eventClass' : Status_Snmp,
                    'component' : 'snmp',
                    'eventGroup' : 'SnmpTest' }

class SnmpPerformanceCollectionTask(BaseTask):
    """
    A task that performs periodic performance collection for devices providing
    data via SNMP agents.
    """
    zope.interface.implements(IScheduledTask)

    STATE_CONNECTING = 'CONNECTING'
    STATE_FETCH_PERF = 'FETCH_PERF_DATA'
    STATE_STORE_PERF = 'STORE_PERF_DATA'

    def __init__(self, 
                 deviceId,
                 taskName, 
                 scheduleIntervalSeconds, 
                 taskConfig):
        """
        @param deviceId: the Zenoss deviceId to watch
        @type deviceId: string
        @param taskName: the unique identifier for this task
        @type taskName: string
        @param scheduleIntervalSeconds: the interval at which this task will be
               collected
        @type scheduleIntervalSeconds: int
        @param taskConfig: the configuration for this task
        """
        super(SnmpPerformanceCollectionTask, self).__init__(
                 deviceId, taskName,
                 taskConfig.cycleInterval, taskConfig
                )

        # Needed for interface
        self.name = taskName
        self.configId = deviceId
        self.state = TaskStates.STATE_IDLE

        # The taskConfig corresponds to a DeviceProxy
        self._device = taskConfig
        self._devId = self._device.id
        self._manageIp = self._device.snmpConnInfo.manageIp
        self._maxOidsPerRequest = self._device.zMaxOIDPerRequest
        log.debug("SnmpPerformanceCollectionTask.__init__: self._maxOidsPerRequest=%s" % self._maxOidsPerRequest)
        self.interval = self._device.cycleInterval
        self._singleOidMode = False
        self._collectedOids = 0

        self._dataService = zope.component.queryUtility(IDataService)
        self._eventService = zope.component.queryUtility(IEventService)

        self._preferences = zope.component.queryUtility(ICollectorPreferences,
                                                        COLLECTOR_NAME)

        self._snmpProxy = None
        self._snmpConnInfo = self._device.snmpConnInfo
        self._oids = self._device.oids
        self._snmpStatusFailures = 0
        self._snmpPort = snmpprotocol.port()
        self._maxbackoffseconds = self._preferences.options.maxbackoffminutes * 60

        self._lastErrorMsg = ''

    def _failure(self, reason):
        """
        Twisted errBack to log the exception for a single device.

        @parameter reason: explanation of the failure
        @type reason: Twisted error instance
        """
        self._snmpStatusFailures += 1
        # Decode the exception
        if isinstance(reason.value, error.TimeoutError):
            msg = ('SNMP agent down (%s second timeout connecting to'
                   ' device %s)') % (self._snmpConnInfo.zSnmpTimeout, self._devId)
            # Indicate that we've handled the error by 
            # not returning a result
            reason = None

        elif isinstance(reason.value, Snmpv3Error):
            msg = ("Cannot connect to SNMP agent on {0._devId}: {1.value}").format(self, reason)
            reason = None

        elif isinstance(reason.value, SingleOidSwitchException):
            return # Just wait for the next cycle

        else:
            msg = reason.getErrorMessage()
            if not msg: # Sometimes we get blank error messages
                msg = reason.__class__
            msg = '%s %s' % (self._devId, msg)

            # Leave 'reason' alone to generate a traceback

        if self._lastErrorMsg != msg:
            self._lastErrorMsg = msg
            if msg:
                log.error(msg)

        self._eventService.sendEvent(STATUS_EVENT,
                                     device=self._devId,
                                     summary=msg,
                                     severity=Event.Error)
        self._delayNextCheck()

        return reason

    def _connectCallback(self, result):
        """
        Callback called after a successful connect to the remote device.
        """
        # If we want to model things first before doing collection,
        # that code goes here.
        log.debug("Connected to %s [%s]", self._devId, self._manageIp)
        self._collectedOids = 0
        return result

    def _fetchPerf(self, ignored):
        """
        Get performance data for all the monitored components on a device

        @parameter ignored: required to keep Twisted's callback chain happy
        @type ignored: result of previous callback
        """
        self.state = SnmpPerformanceCollectionTask.STATE_FETCH_PERF
        if not self._oids:
            return defer.succeed(([]))

        # Either get as many OIDs as we can or one-by-one
        oidsPerRequest = self._maxOidsPerRequest if not self._singleOidMode else 1
        log.debug("Retrieving OIDs from %s [%s] oidsPerRequest=%s", self._devId, self._manageIp, oidsPerRequest)

        d = Chain(self._get, iter(self.chunk(self._oids.keys(), oidsPerRequest))).run()
        d.addCallback(self._checkOidResults)
        d.addCallback(self._storeOidResults)
        d.addCallback(self._updateStatus)
        d.addErrback(self._failure)
        return d

    def _checkOidResults(self, results):
        """
        Decode responses from the device and sanity check the responses

        @parameter results: results of SNMP gets
        @type results: array of (boolean, dictionaries)
        """
        if not results:
            summary = 'Unable to retrieve OIDs from device %s' % \
                        self._devId
            self._eventService.sendEvent(STATUS_EVENT,
                                         device=self._devId,
                                         summary=summary,
                                         severity=Event.Error)
            log.info(summary)
            return defer.fail(summary)

        # Look for problems
        for success, update in results:
            # empty update is probably a bad OID in the request somewhere
            if success and not update and not self._singleOidMode:
                self._singleOidMode = True
                msg = 'Error collecting data on %s -- retrying in single-OID mode' % \
                              self._devId
                log.warn(msg)
                return defer.fail(SingleOidSwitchException(msg))       # Wait for the next cycle

            if not success:
                if isinstance(update, Failure) and \
                    isinstance(update.value, (error.TimeoutError, Snmpv3Error)):
                    return defer.fail(update)
                else:
                    log.warning('Failed to collect on %s (%s: %s)',
                                     self._devId,
                                     update.__class__,
                                     update)
        return results

    def _storeOidResults(self, results):
        """
        Store the OID values in RRD files

        @parameter results: results of SNMP gets
        @type results: array of (boolean, dictionaries)
        """
        self.state = SnmpPerformanceCollectionTask.STATE_STORE_PERF
        oidsReceived = set()
        successCount = 0
        for success, update in results:
            if not success:
                continue

            successCount += 1

            # Casting update to a dict here is unnecessary in all known cases.
            # See ticket #7347 for a bug where update would be a tuple at this
            # point instead of a dict. This cast fixes that problem.
            for oid, value in dict(update).items():
                oid = oid.strip('.')
                if oid not in self._oids:
                    log.error("OID %s is not in %s", oid, self._oids.keys())
                    continue

                # We should always get something useful back
                if value == '' or value is None:
                    log.debug("Got bad value: oid=%s value=%s" % (oid, value))
                    self._badOid(oid)
                    continue
           
                self._collectedOids += 1
                oidsReceived.add(oid)
                # An OID's data can be stored multiple times
                for rrdMeta in self._oids[oid]:
                    cname, path, rrdType, rrdCommand, rrdMin, rrdMax = rrdMeta
                    self._dataService.writeRRD(path, value, rrdType,
                                               rrdCommand=rrdCommand,
                                               min=rrdMin, max=rrdMax)

        if successCount == len(results) and self._singleOidMode:
            # Remove any oids that didn't report
            for doomed in set(self._oids.keys()) - oidsReceived:
                log.debug("Removing OID %s (no response)" % doomed)
                self._badOid(doomed)

        success = True
        if results:
            success = successCount > 0

        return success

    def _finished(self, result):
        """
        Callback activated when the task is complete

        @parameter result: results of SNMP gets
        @type result: array of (boolean, dictionaries)
        """
        if not isinstance(result, Failure):
            log.debug("Device %s [%s] %d of %d OIDs scanned successfully",
                      self._devId, self._manageIp, self._collectedOids,
                      len(self._oids.keys()))
            self._returnToNormalSchedule()
        else:
            log.debug("Device %s [%s] scanned failed, %s",
                      self._devId, self._manageIp, result.getErrorMessage())

        try:
            self._close()
        except Exception, ex:
            log.warn("Failed to close device %s: error %s" %
                     (self._devId, str(ex)))

        # Return the result so the framework can track success/failure
        return result

    def cleanup(self):
        return self._close()

    def doTask(self):
        """
        Contact to one device and return a deferred which gathers data from
        the device.

        @return: A task to scan the OIDs on a device.
        @rtype: Twisted deferred object
        """
        # See if we need to connect first before doing any collection
        d = defer.maybeDeferred(self._connect)
        d.addCallbacks(self._connectCallback, self._failure)
        d.addCallback(self._fetchPerf)

        # Call _finished for both success and error scenarois
        d.addBoth(self._finished)

        # Wait until the Deferred actually completes
        return d

    def _get(self, oids):
        """
        Perform SNMP get for specified OIDs

        @parameter oids: OIDs to gather
        @type oids: list of strings
        @return: Twisted deferred
        @rtype: Twisted deferred
        """
        return self._snmpProxy.get(oids,
                              self._snmpConnInfo.zSnmpTimeout,
                              self._snmpConnInfo.zSnmpTries)

    def _connect(self):
        """
        Create a connection to the remote device
        """
        self.state = SnmpPerformanceCollectionTask.STATE_CONNECTING
        if (self._snmpProxy is None or
            self._snmpProxy._snmpConnInfo != self._snmpConnInfo):
            self._snmpProxy = self._snmpConnInfo.createSession(
                                   protocol=self._snmpPort.protocol,
                                   allowCache=True)
            self._snmpProxy.open()
        log.debug("SnmpPerformanceCollectionTask._connect: Connected to %s" % self._snmpConnInfo.manageIp)
        return self._snmpProxy

    def _close(self):
        """
        Close down the connection to the remote device
        """
        if self._snmpProxy:
            self._snmpProxy.close()
        self._snmpProxy = None

    def _updateStatus(self, success):
        """
        Send up/down events based on SNMP results

        @parameter success: Did everything work?
        @type success: boolean
        """
        if success:
            # As we might not be the process that detected
            # something was down, always send clear events.
            # These are deduped out by the daemon code.
            summary = 'Gathered all OIDs'
            self._eventService.sendEvent(STATUS_EVENT,
                        device=self._devId, summary=summary,
                        severity=Event.Clear)
            if self._snmpStatusFailures > 0:
                log.info("%s %s", self._devId, summary)
            self._snmpStatusFailures = 0

            if not self._lastErrorMsg:
                log.info("%s returned back to normal operations",
                         self._devId)
            self._lastErrorMsg = ''
            if self.interval != self._device.cycleInterval:
                # Setting the value kicks off observers, so don't
                # reset unless necessary
                self.interval = self._device.cycleInterval

        else:
            summary = 'Failed to collect all OIDs'
            self._eventService.sendEvent(STATUS_EVENT,
                    device=self._devId, summary=summary,
                    severity=Event.Warning)
            log.debug("%s %s", self._devId, summary)
            self._snmpStatusFailures += 1

        return defer.succeed(self._snmpStatusFailures)

    def _badOid(self, oid):
        """
        Report any bad OIDs and then remove the OID so we 
        don't generate any further errors.

        @parameter oid: the OID that is not responding
        @type oid: string
        """
        names = [dp[0] for dp in self._oids[oid]]
        summary = 'Error reading value for %s (%s) on %s' % (
            names, oid, self._devId)
        log.warn(summary)

        del self._oids[oid]

    def displayStatistics(self): 
        """
        Called by the collector framework scheduler, and allows us to
        see how each task is doing.
        """
        display = "%s OIDs: %d inSingleOidMode: %s\n" % (
            self.name, len(self._oids.keys()), self._singleOidMode)
        if self._lastErrorMsg:
            display += "%s\n" % self._lastErrorMsg
        return display


if __name__ == '__main__':
    myPreferences = SnmpPerformanceCollectionPreferences()
    myTaskFactory = SimpleTaskFactory(SnmpPerformanceCollectionTask)
    myTaskSplitter = SimpleTaskSplitter(myTaskFactory)
    daemon = CollectorDaemon(myPreferences, myTaskSplitter)
    daemon.run()

