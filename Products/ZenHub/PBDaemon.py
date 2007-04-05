#!/usr/bin/python
#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''PBDaemon

Base for daemons that connect to zenhub

'''

import Globals
from Products.ZenUtils.ZenDaemon import ZenDaemon
#from Products.ZenUtils.Step import Step
import Products.ZenEvents.Event as Event
from Products.ZenUtils.PBUtil import ReconnectingPBClientFactory
from Products.ZenHub.zenhub import PB_PORT

import socket

from twisted.internet import reactor, defer
from twisted.cred import credentials
from twisted.spread import pb

from Products.ZenEvents.ZenEventClasses import App_Start, App_Stop, Heartbeat

from socket import getfqdn


DEFAULT_HUB_HOST = 'localhost'
DEFAULT_HUB_PORT = PB_PORT
DEFAULT_HUB_USERNAME = 'zenoss'
DEFAULT_HUB_PASSWORD = 'zenoss'

startEvent = {
    'eventClass': App_Start, 
    'summary': 'started',
    'severity': Event.Clear,
    }

stopEvent = {
    'eventClass':App_Stop, 
    'summary': 'stopped',
    'severity': Event.Warning,
    }


DEFAULT_HUB_HOST = 'localhost'
DEFAULT_HUB_PORT = PB_PORT
DEFAULT_HUB_USERNAME = 'admin'
DEFAULT_HUB_PASSWORD = 'zenoss'
DEFAULT_HUB_MONITOR = getfqdn()

class PBDaemon(ZenDaemon, pb.Referenceable):
    
    name = 'pbdaemon'
    initialServices = ['EventService']

    def __init__(self, noopts=0, keeproot=False):
        ZenDaemon.__init__(self, noopts, keeproot)
        self.perspective = None
        self.services = {}
        self.eventQueue = []
        self.startEvent = startEvent.copy()
        self.stopEvent = stopEvent.copy()
        for evt in self.startEvent, self.stopEvent:
            evt.update(dict(component=self.name, device=getfqdn()))
    
    def connect(self):

        d = defer.Deferred()
        
        def gotPerspective(perspective):
            "Every time we reconnect this function is called"
            self.log.warning("Connected to ZenHub")
            self.perspective = perspective
            d2 = self.getInitialServices()
            if d.called:
                self.log.debug('adding stop as getInitialServices errback')
                d2.addErrback(lambda e: self.stop())
            else:
                self.log.debug('chaining getInitialServices with d2')
                d2.chainDeferred(d)
            
        factory = ReconnectingPBClientFactory()
        self.log.debug("Connecting to %s", self.options.hubHost)
        reactor.connectTCP(self.options.hubHost, self.options.hubPort, factory)
        username = self.options.username
        password = self.options.password
        self.log.debug("Logging in as %s", username)
        c = credentials.UsernamePassword(username, password)
        factory.gotPerspective = gotPerspective
        factory.startLogin(c)
        return d

    def eventService(self):
        return self.services['EventService']


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
            return error
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
        def errback(error):
            self.log.error('Unable to connect to zenhub: \n%s' % error)
            self.stop()
        d.addCallback(callback)
        d.addErrback(errback)
        reactor.run()
        self.log.info('%s shutting down' % self.name)

    def sigTerm(self, *unused):
        try:
            ZenDaemon.sigTerm(self, *unused)
        except SystemExit:
            pass

    def stop(self):
        if reactor.running:
            if 'EventService' in self.services:
                self.sendEvent(self.stopEvent)
                # give the reactor some time to send the shutdown event
                # we could get more creative an add callbacks for event
                # sends, which would mean we could wait longer, only as long
                # as it took to send
                reactor.callLater(1, reactor.stop)
            else:
                reactor.stop()
        
    def sendEvent(self, event, **kw):
        ''' Add event to queue of events to be sent.  If we have an event
        service then process the queue.
        '''
        event = event.copy()
        event['agent'] = self.name
        event.update(kw)
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
            self.log.error('Error sending event')
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


    def remote_getName(self):
        return self.name


    def remote_shutdown(self, result):
        self.stop()
        self.sigTerm()


    def buildOptions(self):
        self.parser.add_option('--hub-host',
                                dest='hubHost',
                                default=DEFAULT_HUB_HOST,
                                help='Host of zenhub daemon.'
                                ' Default is %s.' % DEFAULT_HUB_HOST)
        self.parser.add_option('--hub-port',
                                dest='hubPort',
                                default=DEFAULT_HUB_PORT,
                                help='Port zenhub listens on.'
                                    'Default is %s.' % DEFAULT_HUB_PORT)
        self.parser.add_option('--username',
                                dest='username',
                                default=DEFAULT_HUB_USERNAME,
                                help='Username for zenhub login.'
                                    ' Default is %s.' % DEFAULT_HUB_USERNAME)
        self.parser.add_option('--password',
                                dest='password',
                                default=DEFAULT_HUB_PASSWORD,
                                help='Password for zenhub login.'
                                    ' Default is %s.' % DEFAULT_HUB_PASSWORD)
        self.parser.add_option('--monitor', 
                                dest='monitor',
                                default=DEFAULT_HUB_MONITOR,
                                help='Name of monitor instance to use for'
                                    ' configuration.  Default is %s.'
                                    % DEFAULT_HUB_MONITOR)

        ZenDaemon.buildOptions(self)

