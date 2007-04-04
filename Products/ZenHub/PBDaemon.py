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
from Products.ZenUtils.Step import Step
import Products.ZenEvents.Event as Event

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


class PBDaemon(ZenDaemon, pb.Referenceable):
    
    name = 'pbdaemon'
    initialServices = ['EventService']
    
    def __init__(self, noopts=0, keeproot=False):
        ZenDaemon.__init__(self, noopts, keeproot)
        #pb.Referenceable.__init__(self)
        self.perspective = None
        self.services = {}

    
    def connect(self, username, password, host='localhost', port=8789):
        ''' Connect to zenhub.  Returns a deferred.
        '''
        factory = pb.PBClientFactory()
        reactor.connectTCP("localhost", port, factory)
        def callback(result):
            self.perspective = result
            return result
        def errback(error):
            import pdb; pdb.set_trace()
            self.log.error('failed to connect to zenhub')
            return error
        d = factory.login(
                credentials.UsernamePassword(username, password), client=self)
        d.addCallback(callback)
        d.addErrback(errback)
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
        d = self.perspective.callRemote('getService', serviceName, self)
        d.addCallback(callback, serviceName)
        d.addErrback(errback, serviceName)
        return d
        

    def setupConnectionAndServices(self):
        ''' Connects to zenhub and sets up services listed in 
        self.initialServices.
        This is a generator that is used with a call to Step.  
        '''
        self.log.debug('setupConnectAndServices')
        d = self.connect(self.options.username,
                            self.options.password,
                            self.options.hubAddress,
                            self.options.hubPort)
        yield d
        self.log.debug('setting up services %s' %
                ', '.join([n for n in self.initialServices]))
        d = defer.DeferredList(
            [self.getService(name) for name in self.initialServices])
        yield d
        self.connected()


    def connected(self):
        self.log.debug('connected')
        self.eventSvc = self.services['EventService']
        
    
    def run(self):
        self.log.debug('run')
        d = Step(self.setupConnectionAndServices())
        reactor.run()


    def remote_getName(self):
        return self.name


    def remote_shutdown(self, result):
        try:
            self.sigTerm()
        except SystemExit:
            pass
        reactor.stop()


    def buildOptions(self):
        ZenDaemon.buildOptions(self)
        self.parser.add_option('--hub-addr',
                                dest='hubAddress',
                                default='localhost',
                                help='Address of zenhub daemon.'
                                ' Default is localhost.')
        self.parser.add_option('--hub-port',
                                dest='hubPort',
                                default=8789,
                                help='Port zenx listens on.  Default is 8789')
        self.parser.add_option('--username',
                                dest='username',
                                default='admin',
                                help='Username for zenhub login')
        self.parser.add_option('--password',
                                dest='password',
                                default='zenoss',
                                help='Password for zenhub login')

