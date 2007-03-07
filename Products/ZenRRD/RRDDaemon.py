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
from Products.ZenEvents.ZenEventClasses import Perf_Snmp, App_Start, App_Stop
from Products.ZenEvents.ZenEventClasses import Heartbeat
from Products.ZenUtils.TwistedAuth import AuthProxy
from Products.ZenUtils.Utils import basicAuthUrl

from twisted.internet import reactor, error
from twisted.python import failure

from Products.ZenUtils.ZCmdBase import ZCmdBase as Base

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
                device, self.label, thresh, how, value)
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

class FakeProxy:

    def __init__(self, obj):
        self.obj = obj

    def callRemote(self, name, *args, **kwargs):
        from twisted.internet import defer
        try:
            method = getattr(self.obj, name)
            return defer.succeed(method(*args, **kwargs))
        except Exception, ex:
            return defer.fail(ex)


class RRDDaemon(Base):
    'Holds the code common to performance gathering daemons.'

    startevt = {'eventClass':App_Start, 
                'summary': 'started',
                'severity': Event.Clear}
    stopevt = {'eventClass':App_Stop, 
               'summary': 'stopped',
               'severity': BAD_SEVERITY}
    heartbeatevt = {'eventClass':Heartbeat}
    
    agent = None
    properties = ('configCycleInterval',)
    heartBeatTimeout = 60
    configCycleInterval = 20            # minutes
    rrd = None
    shutdown = False

    def __init__(self, name):
        self.events = []
        Base.__init__(self)
        self.agent = name
        for ev in self.startevt, self.stopevt, self.heartbeatevt:
            ev['component'] = name
            ev['device'] = socket.getfqdn()
        try:
            monitor = self.options.monitor or socket.getfqdn()
            self.model = FakeProxy(self.getDmdObj('/Monitors/Performance/'+
                                                  monitor))
            self.zem = FakeProxy(self.getDmdObj('/ZenEventManager'))
        except KeyError, ex:
            self.log.debug("Not directly connected (%s) using Zope access.", ex)
            self.model = self.buildProxy(self.options.zopeurl)
            self.zem = self.buildProxy(self.options.zem)

    def buildProxy(self, url):
        "create AuthProxy objects with our config and the given url"
        return AuthProxy(url,
                         self.options.zopeusername,
                         self.options.zopepassword)


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


    def sendEvent(self, event, now=False, **kw):
        'convenience function for pushing an event to the Zope server'
        ev = COMMON_EVENT_INFO.copy()
        ev['agent'] = self.agent
        ev.update(event)
        ev.update(kw)
        self.events.append(ev)
        if now:
            self.sendEvents()
        else:
            reactor.callLater(1, self.sendEvents)


    def sendEvents(self):
        'convenience function for flushing events to the Zope server'
        if self.events:
            d = self.zem.callRemote('sendEvents', self.events)
            d.addBoth(self.eventsSent, self.events)
            self.events = []

    def eventsSent(self, result, events):
        if isinstance(result, failure.Failure):
            if isinstance(result.value, error.ConnectionRefusedError):
                self.log.error("Unable to talk to zenxevents daemon")
            else:
                self.error(result)
            self.events.extend(events)
        else:
            self.events = self.events[len(events):]
            if self.shutdown:
                self._shutdown()

    def sigTerm(self, *unused):
        'controlled shutdown of main loop on interrupt'
        try:
            Base.sigTerm(self, *unused)
        except SystemExit:
            self._shutdown()

    def _shutdown(self):
        self.shutdown = True
        if not self.events:
            reactor.callLater(0, reactor.stop)
        else:
            self.log.debug('waiting for events to flush')
            reactor.callLater(5, reactor.stop)

    def heartbeat(self, *unused):
        'if cycling, send a heartbeat, else, shutdown'
        if not self.options.cycle:
            self._shutdown()
            return
        self.sendEvent(self.heartbeatevt, timeout=self.heartBeatTimeout*3)
        self.sendEvents()

    def buildOptions(self):
        Base.buildOptions(self)
        self.parser.add_option(
            "-z", "--zopeurl",
            dest="zopeurl",
            help="XMLRPC url path for performance configuration server",
            default=DEFAULT_URL)
        self.parser.add_option(
            "-u", "--zopeusername",
            dest="zopeusername", help="username for zope server",
            default='admin')
        self.parser.add_option("--zopepassword", dest="zopepassword")
        self.parser.add_option(
            '--zem', dest='zem',
            help="XMLRPC path to an ZenEventManager instance")
        self.parser.add_option('-d',
            '--device', dest='device',
            help="Specify a specific device to monitor",
            default='')
        self.parser.add_option('--monitor', dest='monitor',
            help="Specify a specific name of the monitor configuration")

    def logError(self, msg, error):
        if isinstance(error, failure.Failure):
            from StringIO import StringIO
            s = StringIO()
            error.printTraceback(s)
            self.log.error('%s: %s', msg, s.getvalue())
        else:
            self.log.error('%s %s', msg, error)

    def error(self, error):
        'Log an error, including any traceback data for a failure Exception'
        self.logError('Error', error)
        if not self.options.cycle:
            self._shutdown()

    def errorStop(self, why):
        self.error(why)
        self._shutdown()


