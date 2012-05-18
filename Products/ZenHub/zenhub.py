#! /usr/bin/env python
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

"""zenhub daemon

Provide remote, authenticated, and possibly encrypted two-way
communications with the Model and Event databases.
"""

import Globals

if __name__ == "__main__":
    # Install the 'best' reactor available, BUT only if run as a script.
    from Products.ZenHub import installReactor
    installReactor()

from XmlRpcService import XmlRpcService

import collections
import socket
import time
import pickle

from twisted.cred import portal, checkers, credentials
from twisted.spread import pb, banana
banana.SIZE_LIMIT = 1024 * 1024 * 10

from twisted.internet import reactor, protocol, defer
from twisted.web import server, xmlrpc
from twisted.internet.error import ProcessExitedAlready
from zope.event import notify
from zope.interface import implements
from zope.component import getUtility, getUtilitiesFor, adapts
from ZODB.POSException import POSKeyError

from Products.DataCollector.Plugins import loadPlugins
from Products.Five import zcml
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.Utils import zenPath, getExitMessage, unused, load_config_override, ipv6_available, atomicWrite
from Products.ZenUtils.DaemonStats import DaemonStats
from Products.ZenEvents.Event import Event, EventHeartbeat
from Products.ZenEvents.ZenEventClasses import App_Start
from Products.ZenMessaging.queuemessaging.interfaces import IEventPublisher
from Products.ZenRelations.PrimaryPathObjectManager import PrimaryPathObjectManager
from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.ZenHub.services.RenderConfig import RenderConfig
from Products.ZenHub.interfaces import IInvalidationProcessor, IServiceAddedEvent, IHubCreatedEvent, IHubWillBeCreatedEvent, IInvalidationOid, IHubConfProvider, IHubHeartBeatCheck
from Products.ZenHub.interfaces import IParserReadyForOptionsEvent, IInvalidationFilter
from Products.ZenHub.interfaces import FILTER_INCLUDE, FILTER_EXCLUDE

from Products.ZenHub.PBDaemon import RemoteBadMonitor
pb.setUnjellyableForClass(RemoteBadMonitor, RemoteBadMonitor)

from BTrees.IIBTree import IITreeSet

# Due to the manipulation of sys.path during the loading of plugins,
# we can get ObjectMap imported both as DataMaps.ObjectMap and the
# full-path from Products.  The following gets the class registered
# with the jelly serialization engine under both names:
#
#  1st: get Products.DataCollector.plugins.DataMaps.ObjectMap
from Products.DataCollector.plugins.DataMaps import ObjectMap
#  2nd: get DataMaps.ObjectMap
import sys
sys.path.insert(0, zenPath('Products', 'DataCollector', 'plugins'))
import DataMaps
unused(DataMaps, ObjectMap)

from Products.ZenHub import XML_RPC_PORT
from Products.ZenHub import PB_PORT
from Products.ZenHub import ZENHUB_ZENRENDER

class AuthXmlRpcService(XmlRpcService):
    """Provide some level of authentication for XML/RPC calls"""

    def __init__(self, dmd, checker):
        XmlRpcService.__init__(self, dmd)
        self.checker = checker


    def doRender(self, unused, request):
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
                    def error(unused, request):
                        self.unauthorized(request)
                    d.addErrback(error, request)
            except Exception:
                self.unauthorized(request)
        return server.NOT_DONE_YET


class HubAvitar(pb.Avatar):
    """
    Connect collectors to their configuration Services
    """

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
        try:
            service = self.hub.getService(serviceName, instance)
        except Exception:
            self.hub.log.exception("Failed to get service '%s'", serviceName)
            return None
        else:
            if service is not None and listener:
                service.addListener(listener)
            return service

    def perspective_reportingForWork(self, worker):
        """
        Allow a worker register for work.

        @type worker: a pb.RemoteReference
        @param worker: a reference to zenhubworker
        @return None
        """
        worker.busy = False
        self.hub.workers.append(worker)
        def removeWorker(worker):
            if worker in self.hub.workers:
                self.hub.workers.remove(worker)
        worker.notifyOnDisconnect(removeWorker)


class ServiceAddedEvent(object):
    implements(IServiceAddedEvent)
    def __init__(self, name, instance):
        self.name = name
        self.instance = instance


class HubWillBeCreatedEvent(object):
    implements(IHubWillBeCreatedEvent)
    def __init__(self, hub):
        self.hub = hub


class HubCreatedEvent(object):
    implements(IHubCreatedEvent)
    def __init__(self, hub):
        self.hub = hub

class ParserReadyForOptionsEvent(object):
    implements(IParserReadyForOptionsEvent)
    def __init__(self, parser):
        self.parser = parser

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


class WorkerInterceptor(pb.Referenceable):
    """Redirect service requests to one of the worker processes. Note
    that everything else (like change notifications) go through
    locally hosted services."""

    callTime = 0.

    def __init__(self, zenhub, service):
        self.zenhub = zenhub
        self.service = service

    def remoteMessageReceived(self, broker, message, args, kw):
        "Intercept requests and send them down to workers"
        svc = str(self.service.__class__).rpartition('.')[0]
        instance = self.service.instance
        args = broker.unserialize(args)
        kw = broker.unserialize(kw)
        # hide the types in the args: subverting the jelly protection mechanism,
        # but the types just passed through and the worker may not have loaded
        # the required service before we try passing types for that service
        # PB has a 640k limit, not bytes but len of sequences. When args are
        # pickled the resulting string may be larger than 640k, split into
        # 100k chunks
        pickledArgs = pickle.dumps( (args, kw) )
        chunkedArgs=[]
        chunkSize = 102400
        while len(pickledArgs) > chunkSize:
            x = pickledArgs[:chunkSize]
            chunkedArgs.append(x)
            pickledArgs = pickledArgs[chunkSize:]
        else:
            #add any leftovers
            chunkedArgs.append(pickledArgs)

        result = self.zenhub.deferToWorker( (svc, instance, message, chunkedArgs) )
        return broker.serialize(result, self.perspective)

    def __getattr__(self, attr):
        "Implement the HubService interface by forwarding to the local service"
        return getattr(self.service, attr)


class ZenHub(ZCmdBase):
    """
    Listen for changes to objects in the Zeo database and update the
    collectors' configuration.

    The remote collectors connect the ZenHub and request configuration
    information and stay connected.  When changes are detected in the
    Zeo database, configuration updates are sent out to collectors
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
    
    ZenHub does very little work in its own process, but instead dispatches
    the work to a pool of zenhubworkers, running zenhubworker.py. zenhub
    manages these workers with 3 data structures:
    - workers - a list of remote PB instances
    - worker_processes - a set of WorkerRunningProtocol instances
    - workerprocessmap - a dict mapping pid to process instance created
        by reactor.spawnprocess
    Callbacks and handlers that detect worker shutdown update these
    structures automatically. ONLY ONE HANDLER must take care of restarting
    new workers, to avoid accidentally spawning too many workers. This
    handler also verifies that zenhub is not in the process of shutting 
    down, so that callbacks triggered during daemon shutdown don't keep
    starting new workers.
    
    TODO: document invalidation workers
    """

    totalTime = 0.
    totalEvents = 0
    totalCallTime = 0.
    name = 'zenhub'

    def __init__(self):
        """
        Hook ourselves up to the Zeo database and wait for collectors
        to connect.
        """
        # list of remote worker references
        self.workers = []
        self.workTracker = {}
        self.workList = []
        # set of worker protocols
        self.worker_processes=set()
        # map of worker pids -> worker processes
        self.workerprocessmap = {}
        self.shutdown = False
        self.counters = collections.Counter()

        ZCmdBase.__init__(self)
        import Products.ZenHub
        zcml.load_config("hub.zcml", Products.ZenHub)
        notify(HubWillBeCreatedEvent(self))

        self.zem = self.dmd.ZenEventManager
        loadPlugins(self.dmd)
        self.services = {}

        er = HubRealm(self)
        checker = self.loadChecker()
        pt = portal.Portal(er, [checker])
        interface = '::' if ipv6_available() else ''
        reactor.listenTCP(self.options.pbport, pb.PBServerFactory(pt), interface=interface)

        xmlsvc = AuthXmlRpcService(self.dmd, checker)
        reactor.listenTCP(self.options.xmlrpcport, server.Site(xmlsvc), interface=interface)

        #start listening for zenrender requests
        if self.options.graph_proxy:
            self.renderConfig = RenderConfig(self.dmd, ZENHUB_ZENRENDER )

        # responsible for sending messages to the queues
        import Products.ZenMessaging.queuemessaging
        load_config_override('twistedpublisher.zcml', Products.ZenMessaging.queuemessaging)
        notify(HubCreatedEvent(self))
        self.sendEvent(eventClass=App_Start,
                       summary="%s started" % self.name,
                       severity=0)

        self._initialize_invalidation_filters()
        reactor.callLater(5, self.processQueue)

        self.rrdStats = self.getRRDStats()
        for i in range(int(self.options.workers)):
            self.createWorker()

    def stop(self):
        self.shutdown = True

    def _getConf(self):
        confProvider = IHubConfProvider(self)
        return confProvider.getHubConf()

    def getRRDStats(self):
        """
        Return the most recent RRD statistic information.
        """
        rrdStats = DaemonStats()
        perfConf = self._getConf()

        from Products.ZenModel.BuiltInDS import BuiltInDS
        threshs = perfConf.getThresholdInstances(BuiltInDS.sourcetype)
        createCommand = getattr(perfConf, 'defaultRRDCreateCommand', None)
        rrdStats.config(perfConf.id, 'zenhub', threshs, createCommand)

        return rrdStats

    def processQueue(self):
        """
        Periodically (once a second) process database changes

        @return: None
        """
        now = time.time()
        self.syncdb()                   # reads the object invalidations
        try:
            self.doProcessQueue()
        except Exception, ex:
            self.log.exception(ex)
        reactor.callLater(1, self.processQueue)
        self.totalEvents += 1
        self.totalTime += time.time() - now

    def _initialize_invalidation_filters(self):
        filters = (f for n, f in getUtilitiesFor(IInvalidationFilter))
        self._invalidation_filters = []
        for fltr in sorted(filters, key=lambda f:getattr(f, 'weight', 100)):
            fltr.initialize(self.dmd)
            self._invalidation_filters.append(fltr)
        self.log.debug('Registered %s invalidation filters.' %
                       len(self._invalidation_filters))

    def _filter_oids(self, oids):
        app = self.dmd.getPhysicalRoot()
        i = 0
        for oid in oids:
            i += 1
            try:
                obj = app._p_jar[oid]
            except POSKeyError:
                # State is gone from the database. Send it along.
                yield oid
            else:
                if isinstance(obj, (PrimaryPathObjectManager, DeviceComponent)):
                    try:
                        obj = obj.__of__(self.dmd).primaryAq()
                    except (AttributeError, KeyError):
                        # It's a delete. This should go through.
                        yield oid
                    else:
                        included = True
                        for fltr in self._invalidation_filters:
                            result = fltr.include(obj)
                            if result in (FILTER_INCLUDE, FILTER_EXCLUDE):
                                included = (result == FILTER_INCLUDE)
                                break
                        if included:
                            oid = self._transformOid(oid, obj)
                            if oid:
                                yield oid

    def _transformOid(self, oid, obj):
        oidTransform = IInvalidationOid(obj)
        return oidTransform.transformOid(oid)

    def doProcessQueue(self):
        """
        Perform one cycle of update notifications.

        @return: None
        """
        changes_dict = self.storage.poll_invalidations()
        if changes_dict is not None:
            processor = getUtility(IInvalidationProcessor)
            d = processor.processQueue(tuple(set(self._filter_oids(changes_dict))))
            def done(n):
                if n:
                    self.log.debug('Processed %s oids' % n)
            d.addCallback(done)


    def sendEvent(self, **kw):
        """
        Useful method for posting events to the EventManager.

        @type kw: keywords (dict)
        @param kw: the values for an event: device, summary, etc.
        @return: None
        """
        if not 'device' in kw:
            kw['device'] = self.options.monitor
        if not 'component' in kw:
            kw['component'] = self.name
        try:
            self.zem.sendEvent(Event(**kw))
        except Exception:
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
            checker = checkers.FilePasswordDB(self.options.passwordfile)
            # grab credentials for the workers to login
            u, p = checker._loadCredentials().next()
            self.workerUsername, self.workerPassword = u, p
            return checker
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
        @param instance: each service serves only one specific collector
        instances (like 'localhost').  instance defines the collector's
        instance name.
        @return: a service loaded from ZenHub/services or one of the zenpacks.
        """
        # Sanity check the names given to us
        if not self.dmd.Monitors.Performance._getOb(instance, False):
            raise RemoteBadMonitor( "The provided performance monitor '%s'" % \
                 self.options.monitor + " is not in the current list" )

        try:
            return self.services[name, instance]

        except KeyError:
            from Products.ZenUtils.Utils import importClass
            try:
                ctor = importClass(name)
            except ImportError:
                ctor = importClass('Products.ZenHub.services.%s' % name, name)
            try:
                svc = ctor(self.dmd, instance)
            except Exception:
                self.log.exception("Failed to initialize %s", ctor)
                # Module can't be used, so unload it.
                if ctor.__module__ in sys.modules:
                    del sys.modules[ctor.__module__]
                return None
            else:
                if self.options.workers:
                    svc = WorkerInterceptor(self, svc)
                self.services[name, instance] = svc
                notify(ServiceAddedEvent(name, instance))
                return svc

    def deferToWorker(self, args):
        """Take a remote request and queue it for worker processes.

        @type args: tuple
        @param args: the arguments to the remote_execute() method in the worker
        @return: a Deferred for the eventual results of the method call

        """
        d = defer.Deferred()
        svcName, instance, method = args[:3]
        service = self.getService(svcName, instance).service
        priority = service.getMethodPriority(method)

        if self.options.prioritize:
            # Insert job into workList so that it stays sorted by priority.
            for i, job in enumerate(self.workList):
                if priority < job[1]:
                    self.workList.insert(i, (d, priority, args) )
                    break
            else:
                self.workList.append( (d, priority, args) )
        else:
            # Run jobs on a first come, first serve basis.
            self.workList.append( (d, priority, args) )

        self.giveWorkToWorkers()
        return d


    def giveWorkToWorkers(self):
        """Parcel out a method invocation to an available worker process
        """
        self.log.debug("worklist has %d items", len(self.workList))
        if self.options.logworkerstats:
            self._workerStats()
        while self.workList:
            for i, worker in enumerate(self.workers):
                # linear search is not ideal, but simple enough
                if not worker.busy:
                    job = self.getJobForWorker(i)
                    if job is None: continue
                    worker.busy = True
                    def finished(result, finishedWorker, wId):
                        stats = self.workTracker.pop(wId,None)
                        if stats:
                            elapsed  = time.time() - stats[1]
                            self.log.debug("worker %s, work %s finished in %s" % (wId,stats[0], elapsed))
                        finishedWorker.busy = False
                        self.giveWorkToWorkers()
                        return result
                    self.log.debug("Giving %s to worker %d", job[2][2], i)
                    self.counters['workerItems'] += 1
                    if self.options.logworkerstats:
                        jobDesc = "%s:%s.%s" % (job[2][1], job[2][0], job[2][2])
                        self.workTracker[i] = (jobDesc, time.time())
                    d2 = worker.callRemote('execute', *job[2])
                    d2.addBoth(finished, worker, i)
                    d2.chainDeferred(job[0])
                    break
            else:
                self.log.debug("all workers are busy")
                break

    def _workerStats(self):
        with open(zenPath('log', '%s_workerstats' % self.options.monitor), 'w') as f:
            now = time.time()
            for wId in range(len(self.workers)):
                stat = self.workTracker.get(wId, None)
                if stat is None:
                    text = "%s\t[Idle]" % wId
                else:
                    elapsed = now - stat[1]
                    text = "\t".join(map(str,[wId, stat[0], '\t', elapsed]))
                f.write(text + '\n')

    def getJobForWorker(self, workerId):
        if self.options.anyworker:
            return self.workList.pop(0)
        else:
            # Restrict lower priority jobs to a subset of the workers.
            lenWorkers = float(len(self.workers))
            for i in range(len(self.workList)):
                priority = self.workList[i][1]
                if priority < (workerId+1) / lenWorkers:
                    return self.workList.pop(i)

    def createWorker(self):
        """Start a worker subprocess

        @return: None
        """
        # this probably can't happen, but let's make sure
        if len(self.worker_processes) >= self.options.workers:
            self.log.info("already at maximum number of worker processes, no worker will be created")
            return
        # create a config file for the slave to pass credentials
        import os, tempfile
        fd, tmp = tempfile.mkstemp()
        try:
            os.write(fd, "hubport %s\n" % self.options.pbport)
            os.write(fd, "username %s\n" % self.workerUsername)
            os.write(fd, "password %s\n" % self.workerPassword)
            os.write(fd, "logseverity %s\n" % self.options.logseverity)
            os.write(fd, "zodb-cachesize %s\n" % self.options.zodb_cachesize)
        finally:
            os.close(fd)
        # start the worker
        exe = zenPath('bin', 'zenhubworker')

        # watch for output, and generally just take notice
        class WorkerRunningProtocol(protocol.ProcessProtocol):

            def __init__(self, parent):
                self._pid = 0
                self.parent = parent
                self.log = parent.log
                self.tmp = tmp

            @property
            def pid(self):
                return self._pid

            def connectionMade(self):
                self._pid = self.transport.pid
                reactor.callLater(1, self.parent.giveWorkToWorkers)

            def outReceived(self, data):
                self.log.debug("Worker (%d) reports %s" % (self.pid, data.rstrip(),))

            def errReceived(self, data):
                self.log.info("Worker (%d) reports %s" % (self.pid, data.rstrip(),))

            def processEnded(self, reason):
                os.unlink(self.tmp)
                self.parent.worker_processes.discard(self)
                self.parent.workerprocessmap.pop(self.pid, None)
                self.log.warning("Worker (%d) exited with status: %d (%s)",
                                 self.pid,
                                  reason.value.exitCode,
                                  getExitMessage(reason.value.exitCode))
                # if not shutting down, restart a new worker
                if not self.parent.shutdown:
                    self.log.info("Starting new zenhubworker")
                    self.parent.createWorker()

        args = (exe, 'run', '-C', tmp)
        self.log.debug("Starting %s", ' '.join(args))
        prot = WorkerRunningProtocol(self)
        proc = reactor.spawnProcess(prot, exe, args, os.environ)
        self.workerprocessmap[proc.pid] = proc
        self.worker_processes.add(prot)

    def heartbeat(self):
        """
        Since we don't do anything on a regular basis, just
        push heartbeats regularly.

        @return: None
        """
        seconds = 30
        evt = EventHeartbeat(self.options.monitor, self.name, 3*seconds)
        self.zem.sendEvent(evt)
        self.niceDoggie(seconds)
        reactor.callLater(seconds, self.heartbeat)
        r = self.rrdStats
        totalTime = sum(s.callTime for s in self.services.values())
        events = r.counter('totalTime', seconds, int(self.totalTime * 1000))
        events += r.counter('totalEvents', seconds, self.totalEvents)
        events += r.gauge('services', seconds, len(self.services))
        events += r.counter('totalCallTime', seconds, totalTime)
        events += r.gauge('workListLength', seconds, len(self.workList))
        for name, value in self.counters.items():
            events += r.counter(name, seconds, value)
        self.zem.sendEvents(events)

        # persist counters values
        self.saveCounters()
        try:
            hbcheck = IHubHeartBeatCheck(self)
            hbcheck.check()
        except:
            self.log.exception("Error processing heartbeat hook")

    def saveCounters(self):
        atomicWrite(
            zenPath('var/zenhub_counters.pickle'),
            pickle.dumps(self.counters),
            raiseException=False,
        )

    def loadCounters(self):
        try:
            self.counters = pickle.load(open(zenPath('var/zenhub_counters.pickle')))
        except Exception:
            pass

    def main(self):
        """
        Start the main event loop.
        """
        if self.options.cycle:
            self.heartbeat()
        reactor.run()
        for proc in self.workerprocessmap.itervalues():
            try:
                proc.signalProcess('KILL')
            except ProcessExitedAlready:
                pass
            except Exception:
                pass
        getUtility(IEventPublisher).close()

    def buildOptions(self):
        """
        Adds our command line options to ZCmdBase command line options.
        """
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--xmlrpcport', '-x', dest='xmlrpcport',
            type='int', default=XML_RPC_PORT,
            help='Port to use for XML-based Remote Procedure Calls (RPC)')
        self.parser.add_option('--pbport', dest='pbport',
            type='int', default=PB_PORT,
            help="Port to use for Twisted's pb service")
        self.parser.add_option('--passwd', dest='passwordfile',
            type='string', default=zenPath('etc','hubpasswd'),
            help='File where passwords are stored')
        self.parser.add_option('--monitor', dest='monitor',
            default='localhost',
            help='Name of the distributed monitor this hub runs on')
        self.parser.add_option('--workers', dest='workers',
            type='int', default=2,
            help="Number of worker instances to handle requests")
        self.parser.add_option('--prioritize', dest='prioritize',
            action='store_true', default=False,
            help="Run higher priority jobs before lower priority ones")
        self.parser.add_option('--anyworker', dest='anyworker',
            action='store_true', default=False,
            help='Allow any priority job to run on any worker')
        self.parser.add_option('--logworkerstats', dest='logworkerstats',
            action='store_true', default=False,
            help='Log current worker state to $ZENHOME/log/workerstats')
        self.parser.add_option('--no-graph-proxy', dest='graph_proxy',
            action='store_false', default=True,
            help="Don't listen to proxy graph requests to zenrender")
        notify(ParserReadyForOptionsEvent(self.parser))

class DefaultConfProvider(object):
    implements(IHubConfProvider)
    adapts(ZenHub)

    def __init__(self, zenhub):
        self._zenhub = zenhub

    def getHubConf(self):
        zenhub = self._zenhub
        return zenhub.dmd.Monitors.Performance._getOb(zenhub.options.monitor, None)

class DefaultHubHeartBeatCheck(object):
    implements(IHubHeartBeatCheck)
    adapts(ZenHub)

    def __init__(self, zenhub):
        self._zenhub = zenhub

    def check(self):
        pass


if __name__ == '__main__':
    from Products.ZenHub.zenhub import ZenHub
    z = ZenHub()

    # during startup, restore performance counters
    z.loadCounters()

    z.main()

    # during shutdown, attempt to save our performance counters
    z.saveCounters()

