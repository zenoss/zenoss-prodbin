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
from urlparse import urlparse
from hashlib import sha1
from itertools import chain
from functools import partial
from zenoss.collector.publisher.publisher import RedisListPublisher
from zenoss.collector.publisher import publisher
from twisted.cred import credentials
from twisted.internet import reactor, defer
from twisted.internet.error import ConnectionLost, ReactorNotRunning, AlreadyCalled
from twisted.spread import pb
from twisted.python.failure import Failure
import twisted.python.log
from zope.interface import implements
from zope.component import getUtilitiesFor
from ZODB.POSException import ConflictError
import Globals
from Products.ZenUtils.ZenDaemon import ZenDaemon
from Products.ZenEvents.ZenEventClasses import Heartbeat
from Products.ZenUtils.PBUtil import ReconnectingPBClientFactory
from Products.ZenUtils.DaemonStats import DaemonStats
from Products.ZenUtils.Utils import zenPath, atomicWrite
from Products.ZenEvents.ZenEventClasses import App_Start, App_Stop, \
    Clear, Warning
from Products.ZenHub.interfaces import (ICollectorEventFingerprintGenerator,
                                        ICollectorEventTransformer,
                                        TRANSFORM_DROP, TRANSFORM_STOP)
from Products.ZenUtils.metricwriter import MetricWriter
from Products.ZenUtils.metricwriter import DerivativeTracker
from Products.ZenUtils.metricwriter import ThresholdNotifier


class RemoteException(Exception, pb.Copyable, pb.RemoteCopy):
    """Exception that can cross the PB barrier"""

    def __init__(self, msg, tb):
        Exception.__init__(self, msg)
        self.traceback = tb

    def __str__(self):
        return "%s: %s" % (
            Exception.__str__(self), self.traceback or '<no traceback>')

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


class DefaultFingerprintGenerator(object):
    """
    Generates a fingerprint using a checksum of properties of the event.
    """
    implements(ICollectorEventFingerprintGenerator)

    weight = 100

    _IGNORE_FIELDS = ('rcvtime','firstTime','lastTime')

    def generate(self, event):
        fields = []
        for k, v in sorted(event.iteritems()):
            if k not in DefaultFingerprintGenerator._IGNORE_FIELDS:
                if isinstance(v, unicode):
                    v = v.encode('utf-8')
                else:
                    v = str(v)
                fields.extend((k,v))
        return sha1('|'.join(fields)).hexdigest()


def _load_utilities(utility_class):
    """
    Loads ZCA utilities of the specified class.

    @param utility_class: The type of utility to load.
    @return: A list of utilities, sorted by their 'weight' attribute.
    """
    utilities = (f for n, f in getUtilitiesFor(utility_class))
    return sorted(utilities, key=lambda f:getattr(f, 'weight', 100))


class BaseEventQueue(object):

    def __init__(self, maxlen):
        self.maxlen = maxlen

    def append(self, event):
        """
        Appends the event to the queue.

        @param event: The event.
        @return: If the queue is full, this will return the oldest event
                 which was discarded when this event was added.
        """
        raise NotImplementedError()

    def popleft(self):
        """
        Removes and returns the oldest event from the queue. If the queue
        is empty, raises IndexError.

        @return: The oldest event from the queue.
        @raise IndexError: If the queue is empty.
        """
        raise NotImplementedError()

    def extendleft(self, events):
        """
        Appends the events to the beginning of the queue (they will be the
        first ones removed with calls to popleft). The list of events are
        expected to be in order, with the earliest queued events listed
        first.

        @param events: The events to add to the beginning of the queue.
        @type events: list
        @return A list of discarded events that didn't fit on the queue.
        @rtype list
        """
        raise NotImplementedError()

    def __len__(self):
        """
        Returns the length of the queue.

        @return: The length of the queue.
        """
        raise NotImplementedError()

    def __iter__(self):
        """
        Returns an iterator over the elements in the queue (oldest events
        are returned first).
        """
        raise NotImplementedError()


class DequeEventQueue(BaseEventQueue):
    """
    Event queue implementation backed by a deque. This queue does not
    perform de-duplication of events.
    """

    def __init__(self, maxlen):
        super(DequeEventQueue, self).__init__(maxlen)
        self.queue = collections.deque()

    def append(self, event):
        # Make sure every processed event specifies the time it was queued.
        if not 'rcvtime' in event:
            event['rcvtime'] = time.time()

        discarded = None
        if len(self.queue) == self.maxlen:
            discarded = self.popleft()
        self.queue.append(event)
        return discarded

    def popleft(self):
        return self.queue.popleft()

    def extendleft(self, events):
        if not events:
            return events
        available = self.maxlen - len(self.queue)
        if not available:
            return events
        to_discard = 0
        if available < len(events):
            to_discard = len(events) - available
        self.queue.extendleft(reversed(events[to_discard:]))
        return events[:to_discard]

    def __len__(self):
        return len(self.queue)

    def __iter__(self):
        return iter(self.queue)


class DeDupingEventQueue(BaseEventQueue):
    """
    Event queue implementation backed by a OrderedDict. This queue performs
    de-duplication of events (when an event with the same fingerprint is
    seen, the 'count' field of the event is incremented by one instead of
    sending an additional event).
    """

    def __init__(self, maxlen):
        super(DeDupingEventQueue, self).__init__(maxlen)
        self.default_fingerprinter = DefaultFingerprintGenerator()
        self.fingerprinters = \
            _load_utilities(ICollectorEventFingerprintGenerator)
        self.queue = collections.OrderedDict()

    def _event_fingerprint(self, event):
        for fingerprinter in self.fingerprinters:
            event_fingerprint = fingerprinter.generate(event)
            if event_fingerprint is not None:
                break
        else:
            event_fingerprint = self.default_fingerprinter.generate(event)

        return event_fingerprint

    def _first_time(self, event1, event2):
        first = lambda evt: evt.get('firstTime', evt['rcvtime'])
        return min(first(event1), first(event2))

    def append(self, event):
        # Make sure every processed event specifies the time it was queued.
        if not 'rcvtime' in event:
            event['rcvtime'] = time.time()

        fingerprint = self._event_fingerprint(event)
        if fingerprint in self.queue:
            # Remove the currently queued item - we will insert again which
            # will move to the end.
            current_event = self.queue.pop(fingerprint)
            event['count'] = current_event.get('count', 1) + 1
            event['firstTime'] = self._first_time(current_event, event)
            self.queue[fingerprint] = event
            return

        discarded = None
        if len(self.queue) == self.maxlen:
            discarded = self.popleft()

        self.queue[fingerprint] = event
        return discarded

    def popleft(self):
        try:
            return self.queue.popitem(last=False)[1]
        except KeyError:
            # Re-raise KeyError as IndexError for common interface across
            # queues.
            raise IndexError()

    def extendleft(self, events):
        # Attempt to de-duplicate with events currently in queue
        events_to_add = []
        for event in events:
            fingerprint = self._event_fingerprint(event)
            if fingerprint in self.queue:
                current_event = self.queue[fingerprint]
                current_event['count'] = current_event.get('count', 1) + 1
                current_event['firstTime'] = self._first_time(current_event, event)
            else:
                events_to_add.append(event)

        if not events_to_add:
            return events_to_add
        available = self.maxlen - len(self.queue)
        if not available:
            return events_to_add
        to_discard = 0
        if available < len(events_to_add):
            to_discard = len(events_to_add) - available
        old_queue, self.queue = self.queue, collections.OrderedDict()
        for event in events_to_add[to_discard:]:
            self.queue[self._event_fingerprint(event)] = event
        for fingerprint, event in old_queue.iteritems():
            self.queue[fingerprint] = event
        return events_to_add[:to_discard]

    def __len__(self):
        return len(self.queue)

    def __iter__(self):
        return self.queue.itervalues()


class EventQueueManager(object):

    CLEAR_FINGERPRINT_FIELDS = ('device','component','eventKey','eventClass')

    def __init__(self, options, log):
        self.options = options
        self.transformers = _load_utilities(ICollectorEventTransformer)
        self.log = log
        self.discarded_events = 0
        # TODO: Do we want to limit the size of the clear event dictionary?
        self.clear_events_count = {}
        self._initQueues()

    def _initQueues(self):
        maxlen = self.options.maxqueuelen
        queue_type = DeDupingEventQueue if self.options.deduplicate_events \
            else DequeEventQueue
        self.event_queue = queue_type(maxlen)
        self.perf_event_queue = queue_type(maxlen)
        self.heartbeat_event_queue = collections.deque(maxlen=1)

    def _transformEvent(self, event):
        for transformer in self.transformers:
            result = transformer.transform(event)
            if result == TRANSFORM_DROP:
                self.log.debug("Event dropped by transform %s: %s",
                               transformer, event)
                return None
            if result == TRANSFORM_STOP:
                break
        return event

    def _clearFingerprint(self, event):
        return tuple(event.get(field, '')
                     for field in self.CLEAR_FINGERPRINT_FIELDS)

    def _removeDiscardedEventFromClearState(self, discarded):
        #
        # There is a particular condition that could cause clear events to never
        # be sent until a collector restart. Consider the following sequence:
        #
        #   1) Clear event added to queue. This is the first clear event of
        #      this type and so it is added to the clear_events_count
        #      dictionary with a count of 1.
        #   2) A large number of additional events are queued until maxqueuelen
        #      is reached, and so the queue starts to discard events including
        #      the clear event from #1.
        #   3) The same clear event in #1 is sent again, however this time it
        #      is dropped because allowduplicateclears is False and the event
        #      has a > 0 count.
        #
        # To resolve this, we are careful to track all discarded events, and
        # remove their state from the clear_events_count dictionary.
        #
        opts = self.options
        if not opts.allowduplicateclears and opts.duplicateclearinterval == 0:
            severity = discarded.get('severity', -1)
            if severity == Clear:
                clear_fingerprint = self._clearFingerprint(discarded)
                if clear_fingerprint in self.clear_events_count:
                    self.clear_events_count[clear_fingerprint] -= 1

    def _addEvent(self, queue, event):
        if self._transformEvent(event) is None:
            return

        allowduplicateclears = self.options.allowduplicateclears
        duplicateclearinterval = self.options.duplicateclearinterval
        if not allowduplicateclears or duplicateclearinterval > 0:
            clear_fingerprint = self._clearFingerprint(event)
            severity = event.get('severity', -1)
            if severity != Clear:
                # A non-clear event - clear out count if it exists
                self.clear_events_count.pop(clear_fingerprint, None)
            else:
                current_count = self.clear_events_count.get(clear_fingerprint, 0)
                self.clear_events_count[clear_fingerprint] = current_count + 1
                if not allowduplicateclears and current_count != 0:
                    self.log.debug(
                        "allowduplicateclears dropping clear event %r",
                        event)
                    return
                if duplicateclearinterval > 0 and current_count % duplicateclearinterval != 0:
                    self.log.debug(
                        "duplicateclearinterval dropping clear event %r",
                        event)
                    return

        discarded = queue.append(event)
        self.log.debug("Queued event (total of %d) %r", len(self.event_queue),
                       event)
        if discarded:
            self.log.debug("Discarded event - queue overflow: %r", discarded)
            self._removeDiscardedEventFromClearState(discarded)
            self.discarded_events += 1

    def addEvent(self, event):
        self._addEvent(self.event_queue, event)

    def addPerformanceEvent(self, event):
        self._addEvent(self.perf_event_queue, event)

    def addHeartbeatEvent(self, heartbeat_event):
        self.heartbeat_event_queue.append(heartbeat_event)

    @defer.inlineCallbacks
    def sendEvents(self, event_sender_fn):
        # Create new queues - we will flush the current queues and don't want to
        # get in a loop sending events that are queued while we send this batch
        # (the event sending is asynchronous).
        prev_heartbeat_event_queue = self.heartbeat_event_queue
        prev_perf_event_queue = self.perf_event_queue
        prev_event_queue = self.event_queue
        self._initQueues()

        perf_events = []
        events = []
        try:
            def chunk_events():
                chunk_remaining = self.options.eventflushchunksize
                heartbeat_events = []
                num_heartbeat_events = min(chunk_remaining,
                    len(prev_heartbeat_event_queue))
                for i in xrange(num_heartbeat_events):
                    heartbeat_events.append(prev_heartbeat_event_queue.popleft())
                chunk_remaining -= num_heartbeat_events

                perf_events = []
                num_perf_events = min(chunk_remaining,
                    len(prev_perf_event_queue))
                for i in xrange(num_perf_events):
                    perf_events.append(prev_perf_event_queue.popleft())
                chunk_remaining -= num_perf_events

                events = []
                num_events = min(chunk_remaining, len(prev_event_queue))
                for i in xrange(num_events):
                    events.append(prev_event_queue.popleft())
                return heartbeat_events, perf_events, events

            heartbeat_events, perf_events, events = chunk_events()
            while heartbeat_events or perf_events or events:
                self.log.debug(
                    "Sending %d events, %d perf events, %d heartbeats",
                    len(events), len(perf_events), len(heartbeat_events))
                yield event_sender_fn(heartbeat_events + perf_events + events)
                heartbeat_events, perf_events, events = chunk_events()

        except Exception:
            # Restore performance events that failed to send
            perf_events.extend(prev_perf_event_queue)
            discarded_perf_events = self.perf_event_queue.extendleft(perf_events)
            self.discarded_events += len(discarded_perf_events)

            # Restore events that failed to send
            events.extend(prev_event_queue)
            discarded_events = self.event_queue.extendleft(events)
            self.discarded_events += len(discarded_events)

            # Remove any clear state for events that were discarded
            for discarded in chain(discarded_perf_events, discarded_events):
                self.log.debug("Discarded event - queue overflow: %r",
                               discarded)
                self._removeDiscardedEventFromClearState(discarded)
            raise

    @property
    def event_queue_length(self):
        return len(self.event_queue) + len(self.perf_event_queue) + \
            len(self.heartbeat_event_queue)


class PBDaemon(ZenDaemon, pb.Referenceable):
    
    name = 'pbdaemon'
    initialServices = ['EventService']
    heartbeatEvent = {'eventClass':Heartbeat}
    heartbeatTimeout = 60*3
    _customexitcode = 0
    _pushEventsDeferred = None
    
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
            self.log.critical(traceback.format_exc(0))
            sys.exit(1)

        self.rrdStats = DaemonStats()
        self.lastStats = 0
        self.perspective = None
        self.services = {}
        self.eventQueueManager = EventQueueManager(self.options, self.log)
        self.startEvent = startEvent.copy()
        self.stopEvent = stopEvent.copy()
        details = dict(component=self.name, device=self.options.monitor)
        for evt in self.startEvent, self.stopEvent, self.heartbeatEvent:
            evt.update(details)
        self.initialConnect = defer.Deferred()
        self.stopped = False
        self.counters = collections.Counter()
        self.loadCounters()
        self._pingedZenhub = None
        self._connectionTimeout = None
        self._publisher = None
        self._metric_writer = None
        self._derivative_tracker = None

        # Add a shutdown trigger to send a stop event and flush the event queue
        reactor.addSystemEventTrigger('before', 'shutdown', self._stopPbDaemon)

    def publisher(self):
        if not self._publisher:
            host, port = urlparse(self.options.redisUrl).netloc.split(':')
            try:
                port = int(port)
            except ValueError:
                self.log.exception("redis url contains non-integer port " +
                                   "value {port}, defaulting to {default}".
                                   format(port=port, default=publisher.defaultRedisPort))
                port = publisher.defaultRedisPort
            self._publisher = RedisListPublisher(host, port, self.options.metricBufferSize)
        return self._publisher

    def metricWriter(self):
        if not self._metric_writer:
            self._metric_writer = MetricWriter(self.publisher())
        return self._metric_writer

    def derivativeTracker(self):
        if not self._derivative_tracker:
            self._derivative_tracker = DerivativeTracker()
        return self._derivative_tracker

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
        # Cancel the connection timeout timer as it's no longer needed.
        if self._connectionTimeout:
            try:
                self._connectionTimeout.cancel()
            except AlreadyCalled:
                pass
            self._connectionTimeout = None
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
        self._connectionTimeout = reactor.callLater(
                self.options.hubtimeout, timeout, self.initialConnect)
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
        threshold_notifier = ThresholdNotifier(self.sendEvent, None)
        self.rrdStats.config(self.name,
                             self.options.monitor,
                             self.metricWriter(),
                             threshold_notifier,
                             self.derivativeTracker())
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

    def setExitCode(self, exitcode):
        self._customexitcode = exitcode

    def stop(self, ignored=''):
        if reactor.running:
            try:
                reactor.stop()
            except ReactorNotRunning:
                self.log.debug("Tried to stop reactor that was stopped")
        else:
            self.log.debug("stop() called when not running")

    def _stopPbDaemon(self):
        if self.stopped:
            return
        self.stopped = True
        if 'EventService' in self.services:
            # send stop event if we don't have an implied --cycle,
            # or if --cycle has been specified
            if not hasattr(self.options, 'cycle') or \
                    getattr(self.options, 'cycle', True):
                self.sendEvent(self.stopEvent)
                self.log.debug("Sent a 'stop' event")
            if self._pushEventsDeferred:
                self.log.debug("Currently sending events. Queueing next call")
                d = self._pushEventsDeferred
                # Schedule another call to flush any additional queued events
                d.addBoth(lambda unused: self.pushEvents())
            else:
                d = self.pushEvents()
            d.addBoth(lambda unused: self.saveCounters())
            return d

        self.log.debug("No event sent as no EventService available.")
        self.saveCounters()

    def sendEvents(self, events):
        map(self.sendEvent, events)
        
    def sendEvent(self, event, **kw):
        """ Add event to queue of events to be sent.  If we have an event
        service then process the queue.
        """
        generatedEvent = self.generateEvent(event, **kw)
        self.eventQueueManager.addEvent(generatedEvent)
        self.counters['eventCount'] += 1

    def generateEvent(self, event, **kw):
        """ Add event to queue of events to be sent.  If we have an event
        service then process the queue.
        """
        if not reactor.running: return
        event = event.copy()
        event['agent'] = self.name
        event['monitor'] = self.options.monitor
        event['manager'] = self.fqdn
        event.update(kw)
        return event

    @defer.inlineCallbacks
    def pushEventsLoop(self):
        """Periodially, wake up and flush events to ZenHub.
        """
        reactor.callLater(self.options.eventflushseconds, self.pushEventsLoop)
        yield self.pushEvents()
   
        # Record the number of events in the queue every 5 minutes.
        now = time.time()
        if self.rrdStats.name and now >= (self.lastStats + 300):
            self.lastStats = now
            self.rrdStats.gauge(
                'eventQueueLength', self.eventQueueManager.event_queue_length)

    @defer.inlineCallbacks
    def pushEvents(self):
        """Flush events to ZenHub.
        """
        # are we already shutting down?
        if not reactor.running:
            self.log.debug("Skipping event sending - reactor not running.")
            return
        if self._pushEventsDeferred:
            self.log.debug("Skipping event sending - previous call active.")
            return
        try:
            self._pushEventsDeferred = defer.Deferred()

            # are still connected to ZenHub?
            evtSvc = self.services.get('EventService', None)
            if not evtSvc:
                self.log.error("No event service: %r", evtSvc)
                return

            discarded_events = self.eventQueueManager.discarded_events
            if discarded_events:
                self.log.error(
                    'Discarded oldest %d events because maxqueuelen was '
                    'exceeded: %d/%d',
                    discarded_events,
                    discarded_events + self.options.maxqueuelen,
                    self.options.maxqueuelen)
                self.counters['discardedEvents'] += discarded_events
                self.eventQueueManager.discarded_events = 0

            send_events_fn = partial(evtSvc.callRemote, 'sendEvents')
            try:
                yield self.eventQueueManager.sendEvents(send_events_fn)
            except ConnectionLost as ex:
                self.log.error('Error sending event: %s', ex)
        except Exception as ex:
            self.log.exception(ex)
        finally:
            d, self._pushEventsDeferred = self._pushEventsDeferred, None
            d.callback('sent')

    def heartbeat(self):
        """if cycling, send a heartbeat, else, shutdown"""
        if not self.options.cycle:
            self.stop()
            return
        heartbeatEvent = self.generateEvent(self.heartbeatEvent, timeout=self.heartbeatTimeout)
        self.eventQueueManager.addHeartbeatEvent(heartbeatEvent)
        # heartbeat is normally 3x cycle time
        self.niceDoggie(self.heartbeatTimeout / 3)

        # save daemon counter stats
        for name, value in self.counters.items():
            self.log.info("Counter %s, value %d", name, value)
            self.rrdStats.counter(name, value)

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

        self.parser.add_option('--disable-event-deduplication',
                               dest='deduplicate_events',
                               default=True,
                               action='store_false',
                               help='Disable event de-duplication')

        ZenDaemon.buildOptions(self)
