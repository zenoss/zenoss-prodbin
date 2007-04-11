#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
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
import transaction
from zExceptions import NotFound

from XmlRpcService import XmlRpcService

import logging
log = logging.getLogger('zenhub')

XML_RPC_PORT = 8081
PB_PORT = 8789

class AuthXmlRpcService(XmlRpcService):
    "Provide some level of authentication for XML/RPC calls"

    def __init__(self, dmd, checker):
        XmlRpcService.__init__(self, dmd)
        self.checker = checker


    def doRender(self, avatar, request):
        "Render after authentication" 
        return XmlRpcService.render(self, request)


    def unauthorized(self, request):
        "Give a hint to the user that their credentials were bad"
        self._cbRender(xmlrpc.Fault(self.FAILURE, "Unauthorized"), request)

    
    def render(self, request):
        "unpack the authorization header and check the credentials"
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
    "Connect collectors to their configuration Services"

    def __init__(self, hub):
        self.hub = hub


    def perspective_getService(self,
                               serviceName,
                               instance = None,
                               listener = None):
        service = self.hub.getService(serviceName, instance)
        if listener:
            service.addListener(listener)
        return service


class HubRealm(object):
    "Gunk needed to connect PB to a login"
    implements(portal.IRealm)


    def __init__(self, hub):
        self.hubAvitar = HubAvitar(hub)


    def requestAvatar(self, collName, mind, *interfaces):
        if pb.IPerspective not in interfaces:
            raise NotImplementedError
        return pb.IPerspective, self.hubAvitar, lambda:None


class ZenHub(ZCmdBase):
    'Listen for change requests provide them to collectors'

    totalTime = 0.
    totalEvents = 0
    maxTime = 0.
    name = 'zenhub'

    def __init__(self):
        self.changes = []
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
        reactor.callLater(5, self.processQueue)


    def zeoConnect(self):
        """override the kind of zeo connection we have so we
        can get OID invalidations"""
        from ZEO.cache import ClientCache as ClientCacheBase
        class ClientCache(ClientCacheBase):
            def invalidate(s, oid, version, tid):
                self.changes.insert(0, oid)
                ClientCacheBase.invalidate(s, oid, version, tid)

        from ZEO.ClientStorage import ClientStorage as ClientStorageBase
        class ClientStorage(ClientStorageBase):
            ClientCacheClass = ClientCache

        # the cache needs to be persistent to get changes
        # made when it was not running
        if self.options.pcachename is None:
            self.options.pcachename = 'zenhub'
        storage = ClientStorage((self.options.host, self.options.port),
                                client=self.options.pcachename,
                                var=self.options.pcachedir,
                                cache_size=self.options.pcachesize*1024*1024)
        from ZODB import DB
        self.db = DB(storage, cache_size=self.options.cachesize)


    def processQueue(self):
        "Process detected object changes"
        self.syncdb()
        try:
            self.doProcessQueue()
        except Exception, ex:
            self.log.exception(ex)
        reactor.callLater(1, self.processQueue)


    def doProcessQueue(self):
        "Process the changes"
        while self.changes:
            oid = self.changes.pop()
            self.log.debug("Got oid %r" % oid)
            obj = self.dmd._p_jar[oid]
            self.log.debug("Object %r changed" % obj)
            try:
                obj = obj.__of__(self.dmd).primaryAq()
                print "Noticing object %s changed" %obj.getPrimaryUrlPath()
            except AttributeError, ex:
                print "Noticing object %s" %obj
                for s in self.services.values():
                    s.deleted(obj)
            else:
                for s in self.services.values():
                    s.update(obj)


    def sendEvent(self, **kw):
        if not 'device' in kw:
            kw['device'] = getfqdn()
        if not 'component' in kw:
            kw['component'] = self.name
        self.zem.sendEvent(Event(**kw))


    def loadChecker(self):
        "Load the password file"
        try:
            return checkers.FilePasswordDB(self.options.passwordfile)
        except Exception, ex:
            self.log.exception("Unable to load %s", self.options.passwordfile)
        return []


    def getService(self, name, instance):
        "Load services dynamically"
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

        
    def sigTerm(self, signum, frame):
        'controlled shutdown of main loop on interrupt'
        try:
            ZCmdBase.sigTerm(self, signum, frame)
        except SystemExit:
            self.sendEvent(eventClass=App_Stop, 
                           summary="%s stopped" % self.name,
                           severity=4)
            if reactor.running:
                reactor.callLater(1, reactor.stop)


    def main(self):
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
