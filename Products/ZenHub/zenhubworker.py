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
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.PBUtil import ReconnectingPBClientFactory
from twisted.cred import credentials
from twisted.spread import pb
from twisted.internet import reactor
from Products.ZenHub.zenhub import PB_PORT

class zenhubworker(ZCmdBase, pb.Referenceable):
    "Execute ZenHub requests in separate process"

    def __init__(self):
        ZCmdBase.__init__(self)
        self.zem = self.dmd.ZenEventManager
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

    def remote_execute(self, service, instance, method, args, kw):
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
        self.syncdb()
        service = self._getService(service, instance)
        m = getattr(service, 'remote_' + method)
        return m(*args, **kw)

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
