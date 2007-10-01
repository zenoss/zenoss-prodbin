#! /usr/bin/env python 
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
from Products.ZenUtils.Utils import zenPath
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
        """
        Call the inherited render engine after authentication succeeds.
        See @L{XmlRpcService.XmlRpcService.Render}.
        """
        return XmlRpcService.render(self, request)


    def unauthorized(self, request):
        """
        Render an XMLRPC error indicating an authentication failure.
        @type request: HTTPRequest
        @param request: the request for this xmlrpc call.
        @return: None
        """
        self._cbRender(xmlrpc.Fault(self.FAILURE, "Unauthorized"), request)
        
    
    def render(self, request):
        """
        Unpack the authorization header and check the credentials.
        @type request: HTTPRequest
        @param request: the request for this xmlrpc call.
        @return: NOT_DONE_YET
        """
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
        """
        Allow a collector to find a Hub service by name.  It also
        associates the service with a collector so that changes can be
        pushed back out to collectors.
        
        @type serviceName: string
        @param serviceName: a name, like 'EventService'
        @type instance: string
        @param instance: the collector's instance name, like 'localhost'
        @type listener: a remote reference to the collector
        @param listener: the callback interface to the collector
        @return a remote reference to a service
        """
        service = self.hub.getService(serviceName, instance)
        if listener:
            service.addListener(listener)
        return service


class HubRealm(object):
    """
    Following the Twisted authentication framework.
    See http://twistedmatrix.com/projects/core/documentation/howto/cred.html
    """
    implements(portal.IRealm)

    def __init__(self, hub):
        self.hubAvitar = HubAvitar(hub)

    def requestAvatar(self, collName, mind, *interfaces):
        if pb.IPerspective not in interfaces:
            raise NotImplementedError
        return pb.IPerspective, self.hubAvitar, lambda:None


class ZenHub(ZCmdBase):
    """
    Listen for changes to objects in the Zeo database and update the
    collectors' configuration.

    The remote collectors connect the ZenHub and request configuration
    information and stay connected.  When changes are detected in the
    Zeo database configuration updates are sent out to collectors
    asynchronously.  In this way, changes made in the web GUI can
    affect collection immediately, instead of waiting for a
    configuration cycle.

    Each collector uses a different, pluggable service within ZenHub
    to translate objects into configuration and data.  ZenPacks can
    add services for their collectors.  Collectors communicate using
    Twisted's Perspective Broker, which provides authenticated,
    asynchronous, bidirectional method invocation.

    ZenHub also provides an XmlRPC interface to some common services
    to support collectors written in other languages.
    """

    totalTime = 0.
    totalEvents = 0
    maxTime = 0.
    name = 'zenhub'

    def __init__(self):
        """
        Hook ourselves up to the Zeo database and wait for collectors
        to connect.
        """
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
        """
        Override the kind of zeo connection we have so we can listen
        to Zeo object updates.  Updates comes as OID invalidations.

        @return: None
        """
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
        """
        Periodically (once a second) process database changes
        
        @return: None
        """
        self.syncdb()                   # reads the object invalidations
        try:
            self.doProcessQueue()
        except Exception, ex:
            self.log.exception(ex)
        reactor.callLater(1, self.processQueue)


    def doProcessQueue(self):
        """
        Perform one cycle of update notifications.

        @return: None
        """
        while self.changes:
            oid = self.changes.pop()
            self.log.debug("Got oid %r" % oid)
            obj = self.dmd._p_jar[oid]
            self.log.debug("Object %r changed" % obj)
            try:
                obj = obj.__of__(self.dmd).primaryAq()
                self.log.debug("Noticing object %s changed" % obj.getPrimaryUrlPath())
            except AttributeError, ex:
                self.log.debug("Noticing object %s " % obj)
                for s in self.services.values():
                    s.deleted(obj)
            else:
                for s in self.services.values():
                    s.update(obj)


    def sendEvent(self, **kw):
        """
        Useful method for posting events to the EventManager.

        @type kw: keywords (dict)
        @param kw: the values for an event: device, summary, etc.
        @return: None
        """
        if not 'device' in kw:
            kw['device'] = getfqdn()
        if not 'component' in kw:
            kw['component'] = self.name
        try:
            self.zem.sendEvent(Event(**kw))
        except:
            self.log.exception("Unable to send an event")


    def loadChecker(self):
        """
        Load the password file

        @return: an object satisfying the ICredentialsChecker
        interface using a password file or an empty list if the file
        is not available.  Uses the file specified in the --passwd
        command line option.
        """
        try:
            return checkers.FilePasswordDB(self.options.passwordfile)
        except Exception, ex:
            self.log.exception("Unable to load %s", self.options.passwordfile)
        return []


    def getService(self, name, instance):
        """
        Helper method to load services dynamically for a collector.
        Returned instances are cached: reconnecting collectors will
        get the same service object.

        @type name: string
        @param name: the dotted-name of the module to load
        (uses @L{Products.ZenUtils.Utils.importClass})
        @param instance: string
        @param instance: each service serves only one specific collector instances (like 'localhost').  instance defines the collector's instance name.
        @return: a service loaded from ZenHub/services or one of the zenpacks.
        """
        try:
            return self.services[name, instance]
        except KeyError:
            from Products.ZenUtils.Utils import importClass
            try:
                ctor = importClass(name)
            except ImportError:
                ctor = importClass('Products.ZenHub.services.%s' % name, name)
            svc = ctor(self.dmd, instance)
            self.services[name, instance] = svc
            return svc

        
    def heartbeat(self):
        """
        Since we don't do anything on a regular basis, just
        push heartbeats regularly.
        
        @return: None
        """
        seconds = 30
        evt = EventHeartbeat(getfqdn(), self.name, 3*seconds)
        self.zem.sendEvent(evt)
        reactor.callLater(seconds, self.heartbeat)

        
    def sigTerm(self, signum, frame):
        """
        Start a controlled shutdown of main loop on interrupt.

        @param signum: unused.
        @param frame: unused.
        @return: None
        """
        try:
            ZCmdBase.sigTerm(self, signum, frame)
        except SystemExit:
            self.sendEvent(eventClass=App_Stop, 
                           summary="%s stopped" % self.name,
                           severity=4)
            if reactor.running:
                reactor.callLater(1, reactor.stop)


    def main(self):
        """
        Start the main event loop.
        
        @return: None
        """
        reactor.run(installSignalHandlers=False)


    def buildOptions(self):
        """
        Adds our command line options to ZCmdBase command line options.

        @return: None
        """
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--xport',
                               '-x',
                               dest='xmlrpcport',
                               type='int',
                               help='Port to use for XML-based Remote Procedure Calls (RPC)',
                               default=XML_RPC_PORT)
        self.parser.add_option('--pbport', 
                               dest='pbport',
                               type='int',
                               help="Port to use for Twisted's pb service",
                               default=PB_PORT)
        self.parser.add_option('--passwd', 
                               dest='passwordfile',
                               type='string',
                               help='File where passwords are stored',
                               default=zenPath('etc','hubpasswd'))
        

if __name__ == '__main__':
    z = ZenHub()
    z.main()
