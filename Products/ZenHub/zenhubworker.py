###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import Globals
from Products.DataCollector.Plugins import loadPlugins
from Products.ZenHub.zenhub import PB_PORT
from Products.ZenHub.PBDaemon import translateError, RemoteConflictError
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.Utils import unused
from Products.ZenUtils.PBUtil import ReconnectingPBClientFactory
# required to allow modeling with zenhubworker
from Products.DataCollector.plugins import DataMaps
unused(DataMaps)

from twisted.cred import credentials
from twisted.spread import pb
from twisted.internet import reactor
from ZODB.POSException import ConflictError
from transaction import commit

import pickle
import time

class zenhubworker(ZCmdBase, pb.Referenceable):
    "Execute ZenHub requests in separate process"

    def __init__(self):
        ZCmdBase.__init__(self)
        self.zem = self.dmd.ZenEventManager
        loadPlugins(self.dmd)
        self.services = {}
        factory = ReconnectingPBClientFactory()
        self.log.debug("Connecting to %s:%d",
                       self.options.hubhost,
                       self.options.hubport)
        reactor.connectTCP(self.options.hubhost, self.options.hubport, factory)
        self.log.debug("Logging in as %s", self.options.username)
        c = credentials.UsernamePassword(self.options.username,
                                         self.options.password)
        factory.gotPerspective = self.gotPerspective
        def stop(*args):
            reactor.callLater(0, reactor.stop)
        factory.clientConnectionLost = stop
        factory.startLogin(c)

    def gotPerspective(self, perspective):
        "Once we are connected to zenhub, register ourselves"
        d = perspective.callRemote('reportingForWork', self)
        def reportProblem(why):
            self.log.error("Unable to report for work: %s", why)
            reactor.stop()
        d.addErrback(reportProblem)
                        
    def _getService(self, name, instance):
        """Utility method to create the service (like PingConfig)
        for instance (like localhost)

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

    @translateError
    def remote_execute(self, service, instance, method, args):
        """Execute requests on behalf of zenhub
        @type service: string
        @param service: the name of a service, like PingConfig
        
        @type instance: string
        @param instance: each service serves only one specific collector instances (like 'localhost').  instance defines the collector's instance name.
        
        @type method: string
        @param method: the name of the called method, like getPingTree
        
        @type args: tuple
        @param args: arguments to the method
        
        @type kw: dictionary
        @param kw: keyword arguments to the method
        """
        self.log.debug("Servicing %s in %s", method, service)
        now = time.time()
        service = self._getService(service, instance)
        m = getattr(service, 'remote_' + method)
        # now that the service is loaded, we can unpack the arguments
        args, kw = pickle.loads(args)
        def runOnce():
            self.syncdb()
            res = m(*args, **kw)
            commit()
            return res
        try:
            for i in range(4):
                try:
                    return runOnce()
                except RemoteConflictError, ex:
                    pass
            # one last try, but don't hide the exception
            return runOnce()
        finally:
            secs = time.time() - now
            self.log.debug("Time in %s: %.2f", method, secs)
            service.callTime += secs

    def buildOptions(self):
        """Options, mostly to find where zenhub lives
        These options should be passed (by file) from zenhub.
        """
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--hubhost', 
                               dest='hubhost',
                               default='localhost',
                               help="Host to use for connecting to ZenHub")
        self.parser.add_option('--hubport', 
                               dest='hubport',
                               type='int',
                               help="Port to use for connecting to ZenHub",
                               default=PB_PORT)
        self.parser.add_option('--username', 
                               dest='username',
                               help="Login name to use when connecting to ZenHub",
                               default='zenoss')
        self.parser.add_option('--password', 
                               dest='password',
                               help="password to use when connecting to ZenHub",
                               default='zenoss')
        
if __name__ == '__main__':
    zhw = zenhubworker()
    reactor.run()
