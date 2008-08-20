###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__='''PBDaemon

Base for daemons that connect to zenhub

'''

import Globals
import sys
from Products.ZenUtils.ZenDaemon import ZenDaemon
from Products.ZenEvents.ZenEventClasses import Heartbeat
from Products.ZenUtils.PBUtil import ReconnectingPBClientFactory
from Products.ZenUtils.DaemonStats import DaemonStats

from twisted.cred import credentials
from twisted.internet import reactor, defer
from twisted.internet.error import ConnectionLost
from twisted.internet.defer import TimeoutError
from twisted.python.failure import Failure
from twisted.spread import pb

class RemoteException(Exception, pb.Copyable, pb.RemoteCopy):
    "Exception that can cross the PB barrier"
    def __init__(self, msg, tb):
        Exception.__init__(self, msg)
        self.traceback = tb
    def __str__(self):
        return Exception.__str__(self) + self.traceback

pb.setUnjellyableForClass(RemoteException, RemoteException)
        
def translateError(callable):
    def inner(*args, **kw):
        try:
            return callable(*args, **kw)
        except Exception, ex:
            import traceback
            raise RemoteException('Remote exception: %s: %s' % (ex.__class__, ex),
                                  traceback.format_exc())
    return inner

from Products.ZenEvents.ZenEventClasses import App_Start, App_Stop, \
                                                Clear, Warning

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
        return defer.fail(HubDown("ZenHub is down"))

class PBDaemon(ZenDaemon, pb.Referenceable):
    
    name = 'pbdaemon'
    initialServices = ['EventService']
    heartbeatEvent = {'eventClass':Heartbeat}
    heartbeatTimeout = 60*3
    _customexitcode = 0
    
    def __init__(self, noopts=0, keeproot=False):
        ZenDaemon.__init__(self, noopts, keeproot)
        self.rrdStats = DaemonStats()
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

    def gotPerspective(self, perspective):
        ''' This gets called every time we reconnect.
        '''
        self.log.warning("Reconnected to ZenHub")
        self.perspective = perspective
        d2 = self.getInitialServices()
        if self.initialConnect:
            self.log.debug('chaining getInitialServices with d2')
            self.initialConnect, d = None, self.initialConnect
            d2.chainDeferred(d)


    def connect(self):
        factory = ReconnectingPBClientFactory()
        self.log.debug("Connecting to %s", self.options.hubhost)
        reactor.connectTCP(self.options.hubhost, self.options.hubport, factory)
        username = self.options.hubusername
        password = self.options.hubpassword
        self.log.debug("Logging in as %s", username)
        c = credentials.UsernamePassword(username, password)
        factory.gotPerspective = self.gotPerspective
        factory.startLogin(c)
        def timeout(d):
            if not d.called:
                self.log.error('Timeout connecting to zenhub: is it running?')
        reactor.callLater(self.options.hubtimeout, timeout, self.initialConnect)
        return self.initialConnect


    def eventService(self):
        return self.getServiceNow('EventService')
        
        
    def getServiceNow(self, svcName):
        if not self.services.has_key(svcName):
            self.log.warning('No service %s named: ZenHub may be disconnected' % svcName)
        return self.services.get(svcName, None) or FakeRemote()


    def getService(self, serviceName, serviceListeningInterface=None):
        ''' Attempt to get a service from zenhub.  Returns a deferred.
        When service is retrieved it is stashed in self.services with
        serviceName as the key.  When getService is called it will first
        check self.services and if serviceName is already there it will return
        the entry from self.services wrapped in a defer.succeed
        '''
        if self.services.has_key(serviceName):
            return defer.succeed(self.services[serviceName])
        def removeService(ignored):
            self.log.debug('removing service %s' % serviceName)
            if serviceName in self.services:
                del self.services[serviceName]
        def callback(result, serviceName):
            self.log.debug('callback after getting service %s' % serviceName)
            self.services[serviceName] = result
            result.notifyOnDisconnect(removeService)
            return result
        def errback(error, serviceName):
            self.log.debug('errback after getting service %s' % serviceName)
            self.log.error('Could not retrieve service %s' % serviceName)
            if serviceName in self.service:
                del self.services[serviceName]
            #return error
        d = self.perspective.callRemote('getService',
                                        serviceName,
                                        self.options.monitor,
                                        serviceListeningInterface or self)
        d.addCallback(callback, serviceName)
        d.addErrback(errback, serviceName)
        return d

    def getInitialServices(self):
        self.log.debug('setting up services %s' %
                ', '.join([n for n in self.initialServices]))
        d = defer.DeferredList(
            [self.getService(name) for name in self.initialServices],
            fireOnOneErrback=True, consumeErrors=True)
        return d


    def connected(self):
        pass
    
    def run(self):
        self.log.debug('run')
        d = self.connect()
        def callback(result):
            self.log.debug('Calling connected.')
            self.log.debug('connected')
            self.sendEvent(self.startEvent)
            self.connected()
            return result
        d.addCallback(callback)
        reactor.run()
        self.log.info('%s shutting down' % self.name)
        if self._customexitcode:
            sys.exit(self._customexitcode)

    def sigTerm(self, signum=None, frame=None):
        try:
            ZenDaemon.sigTerm(self, signum, frame)
        except SystemExit:
            pass

    def stop(self):
        if reactor.running and not self.stopped:
            self.stopped = True
            if 'EventService' in self.services:
                # send stop event if we don't have an implied --cycle,
                # or if --cycle has been specified
                if not hasattr(self.options, 'cycle') or \
                   getattr(self.options, 'cycle', True):
                    self.sendEvent(self.stopEvent)
                # give the reactor some time to send the shutdown event
                # we could get more creative an add callbacks for event
                # sends, which would mean we could wait longer, only as long
                # as it took to send
                reactor.callLater(1, reactor.stop)
            else:
                reactor.stop()

    def sendEvents(self, events):
        map(self.sendEvent, events)
        
    def sendEvent(self, event, **kw):
        ''' Add event to queue of events to be sent.  If we have an event
        service then process the queue.
        '''
        if not reactor.running: return
        event = event.copy()
        event['agent'] = self.name
        event['manager'] = self.options.monitor
        event.update(kw)
        self.log.debug("Sending event %r", event)
        def errback(error, event):
            # If we get an error when sending an event we add it back to the 
            # queue.  This is great if the eventservice is just temporarily
            # unavailable.  This is not so good if there is a problem with
            # this event in particular, in which case we'll repeatedly 
            # attempt to send it.  We need to do some analysis of the error
            # before sticking event back in the queue.
            #
            # Maybe this is overkill and if we have an operable
            # event service we should just log events that don't get sent
            # and then drop them.
            if reactor.running:
                # don't complain if you get disconnected: you'll reconnect
                if not (isinstance(error, Failure) and
                        isinstance(error.value, ConnectionLost)):
                    self.log.error('Error sending event: %s' % error)
                self.eventQueue.append(event)
        if event:
            self.eventQueue.append(event)
        evtSvc = self.services.get('EventService', None)
        if evtSvc:
            for i in range(len(self.eventQueue)):
                event = self.eventQueue[0]
                del self.eventQueue[0]
                d = evtSvc.callRemote('sendEvent', event)
                d.addErrback(errback, event)


    def heartbeat(self):
        'if cycling, send a heartbeat, else, shutdown'
        if not self.options.cycle:
            self.stop()
            return
        self.sendEvent(self.heartbeatEvent, timeout=self.heartbeatTimeout)
        # heartbeat is normally 3x cycle time
        self.niceDoggie(self.heartbeatTimeout / 3)


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
                self.log.exception("Unable to import class %s", c)


    def buildOptions(self):
        self.parser.add_option('--hub-host',
                                dest='hubhost',
                                default=DEFAULT_HUB_HOST,
                                help='Host of zenhub daemon.'
                                ' Default is %s.' % DEFAULT_HUB_HOST)
        self.parser.add_option('--hub-port',
                                dest='hubport',
                                default=DEFAULT_HUB_PORT,
                                help='Port zenhub listens on.'
                                    'Default is %s.' % DEFAULT_HUB_PORT)
        self.parser.add_option('--hub-username',
                                dest='hubusername',
                                default=DEFAULT_HUB_USERNAME,
                                help='Username for zenhub login.'
                                    ' Default is %s.' % DEFAULT_HUB_USERNAME)
        self.parser.add_option('--hub-password',
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
                               help='Initial time to wait for a ZenHub connection')

        ZenDaemon.buildOptions(self)

