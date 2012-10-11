##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Globals
from Products.DataCollector.Plugins import loadPlugins
from Products.ZenHub import PB_PORT
from Products.ZenHub.zenhub import LastCallReturnValue
from Products.ZenHub.PBDaemon import translateError, RemoteConflictError
from Products.ZenUtils.Time import isoDateTime
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.Utils import unused, zenPath
from Products.ZenUtils.PBUtil import ReconnectingPBClientFactory
# required to allow modeling with zenhubworker
from Products.DataCollector.plugins import DataMaps
unused(DataMaps)

from twisted.cred import credentials
from twisted.spread import pb
from twisted.internet import defer, reactor, error
from ZODB.POSException import ConflictError
from collections import defaultdict

import cPickle as pickle
import time
import signal
import os

IDLE = "None/None"
class _CumulativeWorkerStats(object):
    """
    Internal class for maintaining cumulative stats on frequency and runtime
    for individual methods by service
    """
    def __init__(self):
        self.numoccurrences = 0
        self.totaltime = 0.0
        self.lasttime = 0

    def addOccurrence(self, elapsed, now=None):
        if now is None:
            now = time.time()
        self.numoccurrences += 1
        self.totaltime += elapsed
        self.lasttime = now

class zenhubworker(ZCmdBase, pb.Referenceable):
    "Execute ZenHub requests in separate process"

    def __init__(self):
        ZCmdBase.__init__(self)

        self.current = IDLE
        self.currentStart = 0
        self.numCalls = 0
        try:
            self.log.debug("establishing SIGUSR2 signal handler")
            signal.signal(signal.SIGUSR2, self.sighandler_USR2)
        except ValueError:
            # If we get called multiple times, this will generate an exception:
            # ValueError: signal only works in main thread
            # Ignore it as we've already set up the signal handler.
            pass

        self.zem = self.dmd.ZenEventManager
        loadPlugins(self.dmd)
        self.pid = os.getpid()
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

    def sighandler_USR2(self, *args):
        self.reportStats()

    def reportStats(self):
        now = time.time()
        if self.current != IDLE:
            self.log.debug("(%d) Currently performing %s, elapsed %.2f s",
                            self.pid, self.current, now-self.currentStart)
        else:
            self.log.debug("(%d) Currently IDLE", self.pid)
        if self.services:
            loglines = ["(%d) Running statistics:" % self.pid]
            for svc,svcob in sorted(self.services.iteritems(), key=lambda kvp:(kvp[0][1], kvp[0][0].rpartition('.')[-1])):
                svc = "%s/%s" % (svc[1], svc[0].rpartition('.')[-1])
                for method,stats in sorted(svcob.callStats.items()):
                    loglines.append(" - %-48s %-32s %8d %12.2f %8.2f %s" %
                                    (svc, method, 
                                     stats.numoccurrences, 
                                     stats.totaltime, 
                                     stats.totaltime/stats.numoccurrences if stats.numoccurrences else 0.0,
                                     isoDateTime(stats.lasttime)))
            self.log.debug('\n'.join(loglines))
        else:
            self.log.debug("no service activity statistics")

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

            # dict for tracking statistics on method calls invoked on this service,
            # including number of times called and total elapsed time, keyed
            # by method name
            svc.callStats = defaultdict(_CumulativeWorkerStats)

            return svc

    @translateError
    @defer.inlineCallbacks
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
        svcstr = service.rpartition('.')[-1]
        self.current = "%s/%s" % (svcstr, method)
        self.log.debug("Servicing %s in %s", method, service)
        now = time.time()
        self.currentStart = now
        try:
            yield self.async_syncdb()
        except RemoteConflictError, ex:
            pass
        service = self._getService(service, instance)
        m = getattr(service, 'remote_' + method)
        # now that the service is loaded, we can unpack the arguments
        joinedArgs = "".join(args)
        args, kw = pickle.loads(joinedArgs)

        # see if this is our last call
        self.numCalls += 1
        lastCall = self.numCalls >= self.options.calllimit

        def runOnce():
            res = m(*args, **kw)
            if lastCall:
                res = LastCallReturnValue(res)
            pickled_res = pickle.dumps(res, pickle.HIGHEST_PROTOCOL)
            chunkedres=[]
            chunkSize = 102400
            while pickled_res:
                chunkedres.append(pickled_res[:chunkSize])
                pickled_res = pickled_res[chunkSize:]
            return chunkedres
        try:
            for i in range(4):
                try:
                    yield self.async_syncdb()
                    result = runOnce()
                    defer.returnValue(result)
                except RemoteConflictError, ex:
                    pass
            # one last try, but don't hide the exception
            yield self.async_syncdb()
            result = runOnce()
            defer.returnValue(result)
        finally:
            finishTime = time.time()
            secs = finishTime - now
            self.log.debug("Time in %s: %.2f", method, secs)
            # update call stats for this method on this service
            service.callStats[method].addOccurrence(secs, finishTime)
            service.callTime += secs
            self.current = IDLE

            if lastCall:
                reactor.callLater(1, self._shutdown)

    def _shutdown(self):
        self.log.info("Shutting down")
        self.reportStats()
        self.log.info("Stopping reactor")
        try:
            reactor.stop()
        except error.ReactorNotRunning:
            pass

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
        self.parser.add_option('--calllimit',
                               dest='calllimit',
                               type='int',
                               help="Maximum number of remote calls before restarting worker",
                               default=200)

if __name__ == '__main__':
    zhw = zenhubworker()
    reactor.run()
