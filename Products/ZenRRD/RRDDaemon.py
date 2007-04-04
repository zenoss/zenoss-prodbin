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
#from Products.ZenUtils.TwistedAuth import AuthProxy
from Products.ZenUtils.Utils import basicAuthUrl
from Products.ZenUtils.Driver import drive, driveLater
from Products.ZenHub.zenhub import PB_PORT

from Products.ZenUtils.PBUtil import ReconnectingPBClientFactory
from twisted.cred import credentials
from twisted.internet import reactor, error, defer
from twisted.python import failure
from twisted.web.xmlrpc import Proxy

from Products.ZenUtils.ZenDaemon import ZenDaemon as Base

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
    hubService = 'PerformanceConfig'

    def __init__(self, name):
        self.events = []
        Base.__init__(self)
        self.agent = name
        for ev in self.startevt, self.stopevt, self.heartbeatevt:
            ev['component'] = name
            ev['device'] = socket.getfqdn()

    def connect(self):
        d = defer.Deferred()
        def gotPerspective(perspective):
            "Every time we reconnect this function is called"
            def go(driver):
                "Fetch the services we want"
                self.log.debug("Getting event service")
                yield perspective.callRemote('getService', 'EventService',
                                             self.options.monitor)
                self.zem = driver.next()
                if not self.zem:
                    raise failure.Failure("Cannot get EventManager Service")

                self.log.debug("Getting Perf service")
                yield perspective.callRemote('getService', self.hubService,
                                             self.options.monitor)
                self.model = driver.next()
                if not self.model:
                    raise failure.Failure("Cannot get %s Service" %
                                          (self.hubService,))
            self.log.warning("Reconnected to ZenHub")
            d2 = drive(go)
            if not d.called:
                d2.chainDeferred(d)
            
        factory = ReconnectingPBClientFactory()
        self.log.debug("Connecting to %s", self.options.host)
        reactor.connectTCP(self.options.host, self.options.port, factory)
        username = self.options.username
        password = self.options.password
        self.log.debug("Logging in as %s", username)
        c = credentials.UsernamePassword(username, password)
        factory.gotPerspective = gotPerspective
        factory.startLogin(c)
        return d

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
        self.parser.add_option('--host',
                    dest="host",default="localhost",
                    help="hostname of zeo server")
        self.parser.add_option('--port',
                    dest="port",type="int", default=PB_PORT,
                    help="port of zeo server")
        self.parser.add_option("-u", "--username",
                               dest="username", help="username for hub server",
                               default='admin')
        self.parser.add_option("--password", dest="password", default="zenoss")
        self.parser.add_option('-d', '--device', dest='device',
                               help="Specify a specific device to monitor",
                               default='')
        self.parser.add_option('--monitor', dest='monitor', default=socket.getfqdn(),
            help="Specify a specific name of the monitor configuration")

    def logError(self, msg, error):
        if isinstance(error, failure.Failure):
            self.log.exception(error)
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

