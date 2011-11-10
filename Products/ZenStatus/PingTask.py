###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2010, 2011 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """PingTask

Determines the availability of a IP addresses using ping (ICMP).

"""

import re
import time
import logging
log = logging.getLogger("zen.zenping")

from twisted.python.failure import Failure
from twisted.internet import defer

import Globals
from zope import interface
from zope import component

from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_CLEAR

from Products.ZenRRD.zencommand import Cmd, ProcessRunner, TimeoutError
from Products.ZenCollector import interfaces 
from Products.ZenCollector.tasks import TaskStates, BaseTask

from Products.ZenUtils.Utils import unused
from Products.ZenCollector.services.config import DeviceProxy
unused(DeviceProxy)

from Products.ZenEvents.ZenEventClasses import Status_Ping
from Products.ZenEvents import Event
from Products.ZenEvents import ZenEventClasses 
from zenoss.protocols.protobufs import zep_pb2 as events

from Products.ZenUtils.IpUtil import ipunwrap
from interfaces import IPingTask

COLLECTOR_NAME = "zenping"

STATUS_EVENT = { 
    'eventClass' : Status_Ping,
    'component' : 'zenping',
'    eventGroup' : 'Ping'
}
SUPPRESSED = 2

class PingTask(BaseTask):
    interface.implements(IPingTask)

    STATE_PING_START = 'PING_START'
    STATE_PING_STOP  = 'PING_STOP'
    STATE_STORE_PERF = 'STORE_PERF_DATA'

    def __init__(self, taskName, deviceId, scheduleIntervalSeconds, taskConfig):
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
        super(PingTask, self).__init__(
              taskName, deviceId,
              scheduleIntervalSeconds, taskConfig
              )

        # Needed for interface
        self.name = taskName
        self.configId = deviceId
        self.state = TaskStates.STATE_IDLE

        # The taskConfig corresponds to a DeviceProxy
        self._device = taskConfig
        self._devId = deviceId
        self._manageIp = ipunwrap(self._device.manageIp)
        self.interval = scheduleIntervalSeconds
        self._pingResult = None

        self._trace = tuple()
        self._isUp = None
        self._daemon = component.queryUtility(interfaces.ICollector)
        self._dataService = component.queryUtility(interfaces.IDataService)
        self._eventService = component.queryUtility(interfaces.IEventService)
        self._preferences = component.queryUtility(interfaces.ICollectorPreferences,
                                                        COLLECTOR_NAME)
        # Split up so that every interface's IP gets its own ping job
        self.config = self._device.monitoredIps[0]
        self._iface = self.config.iface
        self._lastErrorMsg = ''

    def doTask(self):
        """
        Contact to one device and return a deferred which gathers data from
        the device.

        @return: A task to ping the device and any of its interfaces.
        @rtype: Twisted deferred object
        """
        raise NotImplementedError()

    @property
    def trace(self):
        return self._trace

    @property
    def isUp(self):
        if self._pingResult is None:
            return None
        return self._pingResult.isUp

    def logPingResult(self, pingResult):
        """
        Log the PingResult; set ping state, log to rrd.
        """
        if pingResult is None:
            raise ValueError("pingResult can not be None")     
        self._pingResult = pingResult
        if pingResult.trace:
            self._trace = pingResult.trace
        if pingResult.isUp:
            self._storeResults()

    def sendPingEvent(self, msgTpl, severity, rootCause=None):
        """
        Send an event based on a ping job to the event backend.
        """
        msg = msgTpl % self._devId
        evt = dict(
            device=self._devId,
            ipAddress=self.config.ip,
            summary=msg,
            severity=severity,
            eventClass=ZenEventClasses.Status_Ping,
            eventGroup='Ping',
            component=self._iface,
        )

        if self._pingResult is not None:
            # explicitly set the event time based on the ping collection's time
            if self._pingResult.timestamp:
                evt['lastTime'] = evt['firstTime'] = self._pingResult.timestamp
            # include the last traceroute we know of this is not a Clear    
            if severity and self._pingResult.trace:
                evt['lastTraceroute'] = str(self._pingResult.trace)

        if rootCause:
            devId = rootCause._devid
            evt['rootCause'] = devId
            evt['eventState'] = SUPPRESSED
        return self._eventService.sendEvent(evt)

    def sendPingUp(self, msgTpl='%s is UP!'):
        """
        Send an ping up event to the event backend.
        """
        return self.sendPingEvent(msgTpl, events.SEVERITY_CLEAR)

    def sendPingDown(self, msgTpl='%s is DOWN!', rootCause=None):
        """
        Send an ping down event to the event backend.
        """
        return self.sendPingEvent(msgTpl, events.SEVERITY_CRITICAL, rootCause)

    def _storeResults(self):
        """
        Store the datapoint results asked for by the RRD template.
        """
        if self._pingResult is not None:
            for rrdMeta in self.config.points:
                name, path, rrdType, rrdCommand, rrdMin, rrdMax = rrdMeta
                value = getattr(self._pingResult.rtt, name)
                if value is None:
                    log.debug("No datapoint '%s' found on the %s pingTask",
                              name, self)
                    continue
                self._dataService.writeRRD(
                    path, value, rrdType,
                    rrdCommand=rrdCommand,
                    min=rrdMin, max=rrdMax
                )

