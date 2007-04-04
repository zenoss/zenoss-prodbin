#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''zenxevent

Creates events from xml rpc calls.

$Id$
'''

__version__ = "$Revision$"[11:-2]

from socket import getfqdn
import os


from twisted.cred import portal, checkers, error, credentials
from twisted.spread import pb

from twisted.internet import reactor, defer
from twisted.python import failure
from twisted.web import server, xmlrpc
from zope.interface import implements

import Globals

from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenEvents.Event import Event, EventHeartbeat
from Products.ZenEvents.ZenEventClasses import App_Start, App_Stop

from XmlRpcService import XmlRpcService

import logging
log = logging.getLogger('zenhub')

XML_RPC_PORT = 8081
PB_PORT = 8789

class AuthXmlRpcService(XmlRpcService):

    def __init__(self, dmd, checker):
        XmlRpcService.__init__(self, dmd)
        self.checker = checker

    def doRender(self, avatar, request):
        return XmlRpcService.render(self, request)

    def unauthorized(self, request):
        self._cbRender(xmlrpc.Fault(self.FAILURE, "Unauthorized"), request)
    
    def render(self, request):
        auth = request.received_headers.get('authorization', None)
        if not auth:
            self.unauthorized(request)
        else:
            try:
                type, encoded = auth.split()
                if type not in ('Basic',):
                    self.unauthorized(request)
                else:
                    user, passwd = encoded.decode('base64').split(':')
                    c = credentials.UsernamePassword(user, passwd)
                    d = self.checker.requestAvatarId(c)
                    d.addCallback(self.doRender, request)
                    def error(reason, request):
                        self.unauthorized(request)
                    d.addErrback(error, request)
            except Exception:
                self.unauthorized()
        return server.NOT_DONE_YET

class HubAvitar(pb.Avatar):

    def __init__(self, hub):
        self.hub = hub

    def perspective_getService(self, serviceName, instance):
        return self.hub.getService(serviceName, instance)


class HubRealm(object):
    implements(portal.IRealm)

    def __init__(self, hub):
        self.hubAvitar = HubAvitar(hub)

    def requestAvatar(self, collName, mind, *interfaces):
        log.debug('collName %s' % collName)
        if pb.IPerspective not in interfaces:
            raise NotImplementedError
        return pb.IPerspective, self.hubAvitar, lambda:None 

class ZenHub(ZCmdBase):
    'Listen for xmlrpc requests and turn them into events'

    totalTime = 0.
    totalEvents = 0
    maxTime = 0.
    name = 'zenhub'

    def __init__(self):
        ZCmdBase.__init__(self)
        self.zem = self.dmd.ZenEventManager
        self.services = {}

        er = HubRealm(self)
        checker = self.loadChecker()
        pt = portal.Portal(er, [checker])
        reactor.listenTCP(self.options.pbport, pb.PBServerFactory(pt))

        xmlsvc = AuthXmlRpcService(self.dmd, checker)
        reactor.listenTCP(self.options.xmlrpcport, server.Site(xmlsvc))

        self.sendEvent(eventClass=App_Start, 
                       summary="%s started" % self.name,
                       severity=0)

    def sendEvent(self, **kw):
        if not 'device' in kw:
            kw['device'] = getfqdn()
        if not 'component' in kw:
            kw['component'] = self.name
        self.zem.sendEvent(Event(**kw))

    def loadChecker(self):
        try:
            return checkers.FilePasswordDB(self.options.passwordfile)
        except Exception, ex:
            log.exception("Unable to load %s", self.options.passwordfile)
        return []


    def getService(self, name, instance):
        try:
            return self.services[name, instance]
        except KeyError:
            from Products.ZenUtils.Utils import importClass
            try:
                ctor = importClass(name)
            except ImportError:
                ctor = importClass('services.%s' % name, name)
            svc = ctor(self.dmd, instance)
            self.services[name, instance] = svc
            return svc

        
    def heartbeat(self):
        """Since we don't do anything on a regular basis, just
        push heartbeats regularly"""
        seconds = 30
        evt = EventHeartbeat(getfqdn(), self.name, 3*seconds)
        self.zem.sendEvent(evt)
        reactor.callLater(seconds, self.heartbeat)

        
    def finish(self):
        'things to do at shutdown: thread cleanup, logs and events'
        #self.report()
        self.sendEvent(eventClass=App_Stop, 
                       summary="%s stopped" % self.name,
                       severity=4)


    def sigTerm(self, signum, frame):
        'controlled shutdown of main loop on interrupt'
        try:
            ZCmdBase.sigTerm(self, signum, frame)
        except SystemExit:
            if reactor.running:
                reactor.stop()

    def _wakeUpReactorAndHandleSignals(self):
        self.syncdb()
        reactor.callLater(1.0, self._wakeUpReactorAndHandleSignals)

        
    def main(self):
        reactor.addSystemEventTrigger('before', 'shutdown', self.finish)
        self._wakeUpReactorAndHandleSignals()
        reactor.run(installSignalHandlers=False)


    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--xport',
                               '-x',
                               dest='xmlrpcport',
                               type='int',
                               default=XML_RPC_PORT)
        self.parser.add_option('--pbport', 
                               dest='pbport',
                               type='int',
                               default=PB_PORT)
        self.parser.add_option('--passwd', 
                               dest='passwordfile',
                               type='string',
                               default=os.path.join(os.environ['ZENHOME'],
                                                    'etc','hubpasswd'))
        

if __name__ == '__main__':
    z = ZenHub()
    z.main()
