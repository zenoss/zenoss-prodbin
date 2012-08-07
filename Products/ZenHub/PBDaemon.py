##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """PBDaemon

Base for daemons that connect to zenhub

"""

import cPickle as pickle
import collections
import sys
import time
import traceback

import Globals

from Products.ZenUtils.ZenDaemon import ZenDaemon
from Products.ZenEvents.ZenEventClasses import Heartbeat
from Products.ZenUtils.PBUtil import ReconnectingPBClientFactory
from Products.ZenUtils.DaemonStats import DaemonStats
from Products.ZenUtils.Utils import zenPath, atomicWrite
from Products.ZenUtils.Driver import drive
from Products.ZenEvents.ZenEventClasses import App_Start, App_Stop, \
                                                Clear, Warning

from twisted.cred import credentials
from twisted.internet import reactor, defer
from twisted.internet.error import ConnectionLost, ReactorNotRunning
from twisted.spread import pb
from twisted.python.failure import Failure
import twisted.python.log

from ZODB.POSException import ConflictError

class RemoteException(Exception, pb.Copyable, pb.RemoteCopy):
    "Exception that can cross the PB barrier"
    def __init__(self, msg, tb):
        Exception.__init__(self, msg)
        self.traceback = tb
    def __str__(self):
        return Exception.__str__(self) + self.traceback

pb.setUnjellyableForClass(RemoteException, RemoteException)

# ZODB conflicts
class RemoteConflictError(RemoteException): pass
pb.setUnjellyableForClass(RemoteConflictError, RemoteConflictError)

# Invalid monitor specified
class RemoteBadMonitor(RemoteException): pass

def translateError(callable):
    """
    Decorator function to wrap remote exceptions into something
    understandable by our daemon.

    @parameter callable: function to wrap
    @type callable: function
    @return: function's return or an exception
    @rtype: various
    """
    def inner(*args, **kw):
        """
        Interior decorator
        """
        try:
            return callable(*args, **kw)
        except ConflictError, ex:
            raise RemoteConflictError(
                'Remote exception: %s: %s' % (ex.__class__, ex),
                traceback.format_exc())
        except Exception, ex:
            raise RemoteException(
                'Remote exception: %s: %s' % (ex.__class__, ex),
                traceback.format_exc())
    return inner


PB_PORT = 8789

startEvent = {
    'eventClass': App_Start, 
    'summary': 'started',
    'severity': Clear,
    }

stopEvent = {
    'eventClass':App_Stop, 
    'summary': 'stopped',
    'severity': Warning,
    }


DEFAULT_HUB_HOST = 'localhost'
DEFAULT_HUB_PORT = PB_PORT
DEFAULT_HUB_USERNAME = 'admin'
DEFAULT_HUB_PASSWORD = 'zenoss'
DEFAULT_HUB_MONITOR = 'localhost'

class HubDown(Exception): pass

class FakeRemote:
    def callRemote(self, *unused):
        ex = HubDown("ZenHub is down")
        return defer.fail(ex)

class PBDaemon(ZenDaemon, pb.Referenceable):
    
    name = 'pbdaemon'
    initialServices = ['EventService']
    heartbeatEvent = {'eventClass':Heartbeat}
    heartbeatTimeout = 60*3
    _customexitcode = 0
    _sendingEvents = False
    
    def __init__(self, noopts=0, keeproot=False, name=None):
        # if we were provided our collector name via the constructor instead of
        # via code, be sure to store it correctly.
        if name is not None:
            self.name = name
            self.mname = name

        try:
            ZenDaemon.__init__(self, noopts, keeproot)

        except IOError:
            import traceback
            self.log.critical( traceback.format_exc( 0 ) )
            sys.exit(1)

        self.rrdStats = DaemonStats()
        self.lastStats = 0
        self.perspective = None
        self.services = {}
        self.eventQueue = []
        self.startEvent = startEvent.copy()
        self.stopEvent = stopEvent.copy()
        details = dict(component=self.name, device=self.options.monitor)
        for evt in self.startEvent, self.stopEvent, self.heartbeatEvent:
            evt.update(details)
        self.initialConnect = defer.Deferred()
        self.stopped = False
        self._eventStatus = {}
        self._eventStatusCount = collections.defaultdict(int)
        self.counters = collections.Counter()
        self.loadCounters()
        self._heartbeatEvent = None
        self._performanceEventsQueue = None
        self._pingedZenhub = None

    def connecting(self):
        """
        Called when about to connect to zenhub
        """
        self.log.info("Attempting to connect to zenhub")

    def gotPerspective(self, perspective):
        """
        This gets called every time we reconnect.

        @parameter perspective: Twisted perspective object
        @type perspective: Twisted perspective object
        """
        self.log.info("Connected to ZenHub")
        self.perspective = perspective
        d2 = self.getInitialServices()
        if self.initialConnect:
            self.log.debug('Chaining getInitialServices with d2')
            self.initialConnect, d = None, self.initialConnect
            d2.chainDeferred(d)


    def connect(self):
        pingInterval = self.options.zhPingInterval
        factory = ReconnectingPBClientFactory(connectTimeout=60, pingPerspective=True,
            pingInterval=pingInterval, pingtimeout=pingInterval * 5)
        self.log.info("Connecting to %s:%d" % (self.options.hubhost,
            self.options.hubport))
        factory.connectTCP(self.options.hubhost, self.options.hubport)
        username = self.options.hubusername
        password = self.options.hubpassword
        self.log.debug("Logging in as %s" % username)
        c = credentials.UsernamePassword(username, password)
        factory.gotPerspective = self.gotPerspective
        factory.connecting = self.connecting
        factory.startLogin(c)
        def timeout(d):
            if not d.called:
                self.connectTimeout()
        reactor.callLater(self.options.hubtimeout, timeout, self.initialConnect)
        return self.initialConnect

    def connectTimeout(self):
        self.log.error('Timeout connecting to zenhub: is it running?')
        pass

    def eventService(self):
        return self.getServiceNow('EventService')
        
        
    def getServiceNow(self, svcName):
        if not svcName in self.services:
            self.log.warning('No service named %r: ZenHub may be disconnected' % svcName)
        return self.services.get(svcName, None) or FakeRemote()


    def getService(self, serviceName, serviceListeningInterface=None):
        """
        Attempt to get a service from zenhub.  Returns a deferred.
        When service is retrieved it is stashed in self.services with
        serviceName as the key.  When getService is called it will first
        check self.services and if serviceName is already there it will return
        the entry from self.services wrapped in a defer.succeed
        """
        if serviceName in self.services:
            return defer.succeed(self.services[serviceName])

        def removeService(ignored):
            self.log.debug('Removing service %s' % serviceName)
            if serviceName in self.services:
                del self.services[serviceName]

        def callback(result, serviceName):
            self.log.debug('Loaded service %s from zenhub' % serviceName)
            self.services[serviceName] = result
            result.notifyOnDisconnect(removeService)
            return result

        def errback(error, serviceName):
            self.log.debug('errback after getting service %s' % serviceName)
            self.log.error('Could not retrieve service %s' % serviceName)
            if serviceName in self.services:
                del self.services[serviceName]
            return error

        d = self.perspective.callRemote('getService',
                                        serviceName,
                                        self.options.monitor,
                                        serviceListeningInterface or self)
        d.addCallback(callback, serviceName)
        d.addErrback(errback, serviceName)
        return d

    def getInitialServices(self):
        """
        After connecting to zenhub, gather our initial list of services.
        """
        def errback(error):
            if isinstance(error, Failure):
                self.log.critical( "Invalid monitor: %s" % self.options.monitor)
                reactor.stop()
                return defer.fail(RemoteBadMonitor(
                           "Invalid monitor: %s" % self.options.monitor, ''))
            return error

        self.log.debug('Setting up initial services: %s' % \
                ', '.join(self.initialServices))
        d = defer.DeferredList(
            [self.getService(name) for name in self.initialServices],
            fireOnOneErrback=True, consumeErrors=True)
        d.addErrback(errback)
        return d


    def connected(self):
        pass

    def run(self):
        self.rrdStats.config(self.options.monitor, self.name, [])
        self.log.debug('Starting PBDaemon initialization')
        d = self.connect()
        def callback(result):
            self.sendEvent(self.startEvent)
            self.pushEventsLoop()
            self.log.debug('Calling connected.')
            self.connected()
            return result
        d.addCallback(callback)
        d.addErrback(twisted.python.log.err)
        reactor.run()
        if self._customexitcode:
            sys.exit(self._customexitcode)

    def sigTerm(self, signum=None, frame=None):
        try:
            ZenDaemon.sigTerm(self, signum, frame)
        except SystemExit:
            pass

    def setExitCode(self, exitcode):
        self._customexitcode = exitcode

    def stop(self, ignored=''):
        def stopNow(ignored):
            if reactor.running:
                try:
                    self.saveCounters()
                    reactor.stop()
                except ReactorNotRunning:
                    self.log.debug("Tried to stop reactor that was stopped")
        if reactor.running and not self.stopped:
            self.stopped = True
            if 'EventService' in self.services:
                # send stop event if we don't have an implied --cycle,
                # or if --cycle has been specified
                if not hasattr(self.options, 'cycle') or \
                   getattr(self.options, 'cycle', True):
                    self.sendEvent(self.stopEvent)
                # give the reactor some time to send the shutdown event
                drive(self.pushEvents).addBoth(stopNow)
                self.log.debug( "Sent a 'stop' event" )
            else:
                self.log.debug( "No event sent as no EventService available." )
                # but not too much time
                reactor.callLater(1, stopNow, True) # requires bogus arg
        else:
            self.log.debug( "stop() called when not running" )

    def sendEvents(self, events):
        map(self.sendEvent, events)
        
    def sendEvent(self, event, **kw):
        ''' Add event to queue of events to be sent.  If we have an event
        service then process the queue.
        '''
        generatedEvent = self.generateEvent(event, **kw)
        if generatedEvent:
            self.eventQueue.append(generatedEvent)
            self.counters['eventCount'] += 1 
            self.log.debug("Queued event (total of %d) %r",
                       len(self.eventQueue),
                       generatedEvent)

            # keep the queue in check, but don't trim it all the time
            self._trimEventQueue(maxOver=self.options.eventflushchunksize)

    def generateEvent(self, event, **kw):
        ''' Add event to queue of events to be sent.  If we have an event
        service then process the queue.
        '''
        if not reactor.running: return
        event = event.copy()
        event['agent'] = self.name
        event['monitor'] = self.options.monitor
        event['manager'] = self.fqdn
        event.update(kw)
        if not self.options.allowduplicateclears or self.options.duplicateclearinterval > 0:
            statusKey = ( event['device'],
                          event.get('component', ''),
                          event.get('eventKey', ''),
                          event.get('eventClass', '') )
            severity = event.get('severity', -1)
            status = self._eventStatus.get(statusKey, -1)
            if severity != -1:
               if severity != status:
                   self._eventStatusCount[statusKey] = 0
               else:
                   self._eventStatusCount[statusKey] += 1
            self._eventStatus[statusKey] = severity
            if severity == Clear and status == Clear:
                if not self.options.allowduplicateclears:
                    self.log.debug("allowduplicateclears dropping useless clear event %r", event)
                    return
                if self.options.duplicateclearinterval > 0 \
                    and self._eventStatusCount[statusKey] % self.options.duplicateclearinterval != 0:
                    self.log.debug("duplicateclearinterval dropping useless clear event %r", event)
                    return
        return event 

    def _trimEventQueue(self, maxOver=0):
        queueLen = len(self.eventQueue)
        if queueLen > (self.options.maxqueuelen + maxOver):
            diff = queueLen - self.options.maxqueuelen
            self.log.error(
                'Discarding oldest %d events because maxqueuelen was '
                'exceeded: %d/%d',
                queueLen - self.options.maxqueuelen,
                queueLen, self.options.maxqueuelen)
            self.counters['discardedEvents'] += diff
            self.eventQueue = self.eventQueue[diff:]

    @property
    def _performanceEvents(self):
        if self._performanceEventsQueue is None:
            self._performanceEventsQueue = collections.deque(maxlen=self.options.maxqueuelen)
        return self._performanceEventsQueue
      
    def _getPerformanceEventsChunk(self):
        events = []
        for i in xrange(0, min(len(self._performanceEvents), self.options.eventflushchunksize)):
            events.append(self._performanceEvents.pop())
        return events

    def pushEventsLoop(self):
        """Periodially, wake up and flush events to ZenHub.
        """
        reactor.callLater(self.options.eventflushseconds, self.pushEventsLoop)
        drive(self.pushEvents)
   
        # Record the number of events in the queue every 5 minutes.
        now = time.time()
        if self.rrdStats.name and now >= (self.lastStats + 300):
            self.lastStats = now
            events = self.rrdStats.gauge('eventQueueLength',
                300, len(self.eventQueue))
            self._performanceEvents.extendleft(events)

    def pushEvents(self, driver):
        """Flush events to ZenHub.
        """
        # are we already shutting down?
        if not reactor.running:
            return
        if self._sendingEvents:
            return
        try:
            # try to send everything we have, serially
            self._sendingEvents = True
            while len(self.eventQueue) or self._heartbeatEvent or len(self._performanceEvents):

                # are still connected to ZenHub?
                evtSvc = self.services.get('EventService', None)
                if not evtSvc: 
                    self.log.error("No event service: %r", evtSvc)
                    break
                # send the events in large bundles, carefully reducing
                # the eventQueue in case we get in here more than once
                chunkSize = self.options.eventflushchunksize
                events = self.eventQueue[:chunkSize]
                self.eventQueue = self.eventQueue[chunkSize:]

                performanceEvents = self._getPerformanceEventsChunk()

                # send the events and wait for the response
                heartBeat = [self._heartbeatEvent] if self._heartbeatEvent else []

                self.log.debug("Sending %d events, %d perfevents, %d heartbeats.", len(events), len(performanceEvents), len(heartBeat))
                yield evtSvc.callRemote('sendEvents', events + heartBeat + performanceEvents)
                try:
                    driver.next()
                    performanceEvents = []
                    events = []
                except ConnectionLost, ex:
                    self.log.error('Error sending event: %s' % ex)
                    self.eventQueue = events + self.eventQueue
                    performanceEvents.reverse()
                    self._performanceEvents.extend(performanceEvents)
                    break
                self.log.debug("Events sent")
                self._heartbeatEvent = None
        except Exception, ex:
            self.log.exception(ex)
        finally:
            self._sendingEvents = False

    def heartbeat(self):
        'if cycling, send a heartbeat, else, shutdown'
        if not self.options.cycle:
            self.stop()
            return
        self._heartbeatEvent = self.generateEvent(self.heartbeatEvent, timeout=self.heartbeatTimeout)
        # heartbeat is normally 3x cycle time
        self.niceDoggie(self.heartbeatTimeout / 3)

        events = []
        # save daemon counter stats
        for name, value in self.counters.items():
            self.log.info("Counter %s, value %d", name, value)
            events += self.rrdStats.counter(name, 300, value)
        self.sendEvents(events)

        # persist counters values
        self.saveCounters()

    def saveCounters(self):
        atomicWrite(
            zenPath('var/%s_counters.pickle' % self.name),
            pickle.dumps(self.counters),
            raiseException=False,
        )

    def loadCounters(self):
        try:
            self.counters = pickle.load(open(zenPath('var/%s_counters.pickle'% self.name)))
        except Exception:
            pass

    def remote_getName(self):
        return self.name


    def remote_shutdown(self, unused):
        self.stop()
        self.sigTerm()


    def remote_setPropertyItems(self, items):
        pass


    @translateError
    def remote_updateThresholdClasses(self, classes):
        from Products.ZenUtils.Utils import importClass
        self.log.debug("Loading classes %s", classes)
        for c in classes:
            try:
                importClass(c)
            except ImportError:
                self.log.error("Unable to import class %s", c)


    def buildOptions(self):
        self.parser.add_option('--hubhost',
                                dest='hubhost',
                                default=DEFAULT_HUB_HOST,
                                help='Host of zenhub daemon.'
                                ' Default is %s.' % DEFAULT_HUB_HOST)
        self.parser.add_option('--hubport',
                                dest='hubport',
                                type='int',
                                default=DEFAULT_HUB_PORT,
                                help='Port zenhub listens on.'
                                    'Default is %s.' % DEFAULT_HUB_PORT)
        self.parser.add_option('--hubusername',
                                dest='hubusername',
                                default=DEFAULT_HUB_USERNAME,
                                help='Username for zenhub login.'
                                    ' Default is %s.' % DEFAULT_HUB_USERNAME)
        self.parser.add_option('--hubpassword',
                                dest='hubpassword',
                                default=DEFAULT_HUB_PASSWORD,
                                help='Password for zenhub login.'
                                    ' Default is %s.' % DEFAULT_HUB_PASSWORD)
        self.parser.add_option('--monitor', 
                                dest='monitor',
                                default=DEFAULT_HUB_MONITOR,
                                help='Name of monitor instance to use for'
                                    ' configuration.  Default is %s.'
                                    % DEFAULT_HUB_MONITOR)
        self.parser.add_option('--initialHubTimeout',
                               dest='hubtimeout',
                               type='int',
                               default=30,
                               help='Initial time to wait for a ZenHub '
                                    'connection')
        self.parser.add_option('--allowduplicateclears',
                               dest='allowduplicateclears',
                               default=False,
                               action='store_true',
                               help='Send clear events even when the most '
                               'recent event was also a clear event.')

        self.parser.add_option('--duplicateclearinterval',
                               dest='duplicateclearinterval',
                               default=0,
                               type='int',
                               help=('Send a clear event every [DUPLICATECLEARINTEVAL] '
                                     'events.')
        )

        self.parser.add_option('--eventflushseconds',
                               dest='eventflushseconds',
                               default=5.,
                               type='float',
                               help='Seconds between attempts to flush '
                               'events to ZenHub.')

        self.parser.add_option('--eventflushchunksize',
                               dest='eventflushchunksize',
                               default=50,
                               type='int',
                               help='Number of events to send to ZenHub'
                               'at one time')

        self.parser.add_option('--maxqueuelen',
                               dest='maxqueuelen',
                               default=5000,
                               type='int',
                               help='Maximum number of events to queue')

        self.parser.add_option('--zenhubpinginterval',
                               dest='zhPingInterval',
                               default=30,
                               type='int',
                               help='How often to ping zenhub')

        ZenDaemon.buildOptions(self)
