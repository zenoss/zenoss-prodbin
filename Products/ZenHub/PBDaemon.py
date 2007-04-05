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
#from Products.ZenUtils.Driver import drive
from Products.ZenUtils.Step import Step
import Products.ZenEvents.Event as Event
from Products.ZenUtils.PBUtil import ReconnectingPBClientFactory

from Products.ZenHub.zenhub import PB_PORT

from twisted.internet import reactor, defer
from twisted.cred import credentials
from twisted.spread import pb

App_Start = "/App/Start"
App_Stop = "/App/Stop"
Heartbeat = "/Heartbeat"

startEvent = {
    'eventClass': App_Start, 
    'summary': 'started',
    'severity': Event.Clear,
    'device': '',
    'component': '',
    }
stopEvent = {
    'eventClass':App_Stop, 
    'summary': 'stopped',
    'severity': Event.Warning,
    'device': '',
    'component': '',
    }
#heartbeatEvent = {
#    'eventClass': Event.Heartbeat,
#    'device': '',
#    'component': '',
#    'timeout': 3 * HEARTBEAT_CYCLETIME,
#    }


DEFAULT_HUB_HOST = 'localhost'
DEFAULT_HUB_PORT = PB_PORT
DEFAULT_HUB_USERNAME = 'admin'
DEFAULT_HUB_PASSWORD = 'zenoss'


class PBDaemon(ZenDaemon, pb.Referenceable):
    
    name = 'pbdaemon'
    initialServices = ['EventService']
    
    def __init__(self, noopts=0, keeproot=False):
        ZenDaemon.__init__(self, noopts, keeproot)
        #pb.Referenceable.__init__(self)
        self.perspective = None
        self.services = {}
        self.eventQueue = []

    
    def connect(self):

        def gotPerspective(perspective):
            "Every time we reconnect this function is called"
            self.log.warning("Reconnected to ZenHub")
            self.perspective = perspective
            d2 = self.getInitialServices()
            if not d.called:
                d2.chainDeferred(d)
            
        d = defer.Deferred()
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


    def getService(self, serviceName):
        ''' Attempt to get a service from zenhub.  Returns a deferred.
        When service is retrieved it is stashed in self.services with
        serviceName as the key.  When getService is called it will first
        check self.services and if serviceName is already there it will return
        the entry from self.services wrapped in a defer.succeed
        '''
        if self.services.has_key(serviceName):
            return defer.succeed(self.services[serviceName])
        def callback(result, serviceName):
            self.log.debug('callback after getting service %s' % serviceName)
            self.services[serviceName] = result
            return result
        def errback(error, serviceName):
            self.log.debug('errback after getting service %s' % serviceName)
            self.log.error('Could not retrieve service %s' % serviceName)
            return error
        d = self.perspective.callRemote('getService', serviceName)
        d.addCallback(callback, serviceName)
        d.addErrback(errback, serviceName)
        return d

            
    def getInitialServices(self):
        self.log.debug('setting up services %s' %
                ', '.join([n for n in self.initialServices]))
        d = defer.DeferredList(
            [self.getService(name) for name in self.initialServices])
        return d
        
        
    def connected(self):
        self.log.debug('connected')
        self.eventSvc = self.services['EventService']
        self.eventSvc.callRemote('sendEvent', startEvent)
        
    
    def run(self):
        self.log.debug('run')
        d = self.connect()
        def callback(result):
            self.connected()
            return result
        def errback(error):
            self.log.error('Unable to connect to zenhub.')
            self.stop()
        d.addCallbacks(callback, errback)
        reactor.run()
        self.log.info('%s shutting down' % self.name)


    def stop(self):
        if reactor.running:
            reactor.stop()
        
        
    def sendEvent(self, event=None):
        ''' Add event to queue of events to be sent.  If we have an event
        service then process the queue.
        '''
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
        if self.eventSvc:
            for i in range(len(self.eventQueue)):
                event = self.eventQueue[0]
                del self.eventQueue[0]
                d = self.eventSvc.callRemote('sendEvent', event)
                d.addErrback(errback, event)


    def remote_getName(self):
        return self.name


    def remote_shutdown(self, result):
        self.stop()
        try:
            self.sigTerm()
        except SystemExit:
            pass
        reactor.stop()


    def buildOptions(self):
        ZenDaemon.buildOptions(self)
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

