#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''RRDDaemon

Common performance monitoring daemon code for performance daemons.

$Id$
'''

__version__ = "$Revision$"[11:-2]

import socket

import Globals
from Products.ZenEvents import Event
from Products.ZenEvents.ZenEventClasses import Perf_Snmp, Heartbeat
from Products.ZenUtils.Driver import drive

from twisted.internet import reactor, defer
from twisted.python import failure

from Products.ZenHub.PBDaemon import PBDaemon as Base

BAD_SEVERITY=Event.Warning

BASE_URL = 'http://localhost:8080/zport/dmd'
DEFAULT_URL = BASE_URL + '/Monitors/Performance/localhost'


COMMON_EVENT_INFO = {
    'manager': socket.getfqdn(),
    }

class Threshold:
    'Hold threshold config and send events based on the current value'
    count = 0
    label = ''
    minimum = None
    maximum = None
    eventClass = Perf_Snmp
    severity = Event.Info
    escalateCount = 0

    def __init__(self, label, minimum, maximum, eventClass, severity, count):
        self.label = label
        self.update(minimum, maximum, eventClass, severity, count)


    def update(self, minimum, maximum, eventClass, severity, count):
        self.minimum = minimum
        self.maximum = maximum
        self.eventClass = eventClass
        self.severity = severity
        self.escalateCount = count


    def check(self, device, cname, oid, value, eventCb):
        'Check the value for min/max thresholds, and post events'
        if value is None:
            return
        thresh = None
        if self.maximum is not None and value > self.maximum:
            thresh = self.maximum
            how = 'exceeded'
        if self.minimum is not None and value < self.minimum:
            thresh = self.minimum
            how = 'not met'
        if thresh is not None:
            self.count += 1
            severity = self.severity
            if self.escalateCount and self.count >= self.escalateCount:
                severity += 1
            summary = '%s %s threshold of %s %s: current value %.2f' % (
                device, self.label, thresh, how, float(value))
            eventCb(device=device,
                    summary=summary,
                    eventClass=self.eventClass,
                    eventKey=oid,
                    component=cname,
                    severity=severity)
        else:
            if self.count:
                summary = '%s %s threshold restored current value: %.2f' % (
                    device, self.label, value)
                eventCb(device=device,
                        summary=summary,
                        eventClass=self.eventClass,
                        eventKey=oid,
                        component=cname,
                        severity=Event.Clear)
            self.count = 0

class ThresholdManager:
    "manage a collection of thresholds"
    
    def __init__(self):
        self.thresholds = {}

    def update(self, config):
        before = self.thresholds
        self.thresholds = {}
        for label, minimum, maximum, eventClass, severity, count in config:
            t = before.get(label, None)
            if t:
                t.update(minimum, maximum, eventClass, severity, count)
            else:
                t = Threshold(label, minimum, maximum, eventClass, severity, count)
            self.thresholds[label] = t

    def __iter__(self):
        return iter(self.thresholds.values())

class RRDDaemon(Base):
    'Holds the code common to performance gathering daemons.'

    heartbeatevt = {'eventClass':Heartbeat}
    
    properties = ('configCycleInterval',)
    heartBeatTimeout = 60
    configCycleInterval = 20            # minutes
    rrd = None
    shutdown = False

    def __init__(self, name):
        self.events = []
        Base.__init__(self)
        self.name = name
        evt = self.heartbeatevt.copy()
        self.heartbeatevt.update(dict(component=name,
                                      device=socket.getfqdn()))

    def getDevicePingIssues(self):
        if 'EventService' in self.services:
            return self.services['EventService'].callRemote('getDevicePingIssues')
        return defer.fail("Not connected to ZenHub")

    def remote_setPropertyItems(self, items):
        self.log.debug("Async update of collection properties")
        self.setPropertyItems(items)

    def setPropertyItems(self, items):
        'extract configuration elements used by this server'
        table = dict(items)
        for name in self.properties:
            value = table.get(name, None)
            if value is not None:
                if getattr(self, name) != value:
                    self.log.debug('Updated %s config to %s' % (name, value))
                setattr(self, name, value)


    def sendThresholdEvent(self, **kw):
        "Send the right event class for threshhold events"
        self.sendEvent({}, **kw)

    def heartbeat(self, *unused):
        'if cycling, send a heartbeat, else, shutdown'
        if not self.options.cycle:
            self.stop()
            return
        self.sendEvent(self.heartbeatevt, timeout=self.heartBeatTimeout*3)


    def buildOptions(self):
        Base.buildOptions(self)
        self.parser.add_option('-d', '--device',
                               dest='device',
                               default='',
                               help="Specify a specific device to monitor")

    def logError(self, msg, error):
        if isinstance(error, failure.Failure):
            self.log.exception(error)
        else:
            self.log.error('%s %s', msg, error)

    def error(self, error):
        'Log an error, including any traceback data for a failure Exception'
        self.logError('Error', error)
        if not self.options.cycle:
            self.stop()

    def errorStop(self, why):
        self.error(why)
        self.stop()

    def model(self):
        class Fake:
            def callRemote(self, *args, **kwargs):
                return defer.fail("No connection to ZenHub")
        return self.services.get(self.initialServices[-1], Fake())

