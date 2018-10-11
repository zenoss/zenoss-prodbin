from unittest import TestCase
from mock import Mock, patch, create_autospec, call, MagicMock, sentinel

from zope.interface.verify import verifyObject
from zope.component import adaptedBy

from mock_interface import create_interface_mock

# Breaks test isolation ImportError: No module named Globals
from Products.ZenHub.zenhub import (
    AuthXmlRpcService,
    XmlRpcService,
    HubAvitar,
    RemoteBadMonitor,
    pb,
    ServiceAddedEvent, IServiceAddedEvent,
    HubWillBeCreatedEvent, IHubWillBeCreatedEvent,
    HubCreatedEvent, IHubCreatedEvent,
    ParserReadyForOptionsEvent, IParserReadyForOptionsEvent,
    _ZenHubWorklist,
    publisher,
    redisPublisher,
    ZenHub,
    CONNECT_TIMEOUT, OPTION_STATE,
    IInvalidationFilter,
    POSKeyError,
    PrimaryPathObjectManager,
    DeviceComponent,
    FILTER_INCLUDE, FILTER_EXCLUDE,
    IInvalidationProcessor,
    collections,
    defer,
    LastCallReturnValue,
    XML_RPC_PORT, PB_PORT,
    DefaultConfProvider, IHubConfProvider,
    DefaultHubHeartBeatCheck, IHubHeartBeatCheck,
    IEventPublisher,
    MetricManager,
    ListLengthGauge,
    InvalidationsManager,
    SEVERITY_CLEAR, INVALIDATIONS_PAUSED,
    WorkerManager,
    WorkerSelector,
)

PATH = {'src': 'Products.ZenHub.zenhub'}


class ZenHubInitTest(TestCase):
    '''The init test is seperate from the others due to the complexity
    of the __init__ method
    '''

    @patch('{src}.signal'.format(**PATH))
    @patch('{src}.MetricManager'.format(**PATH))
    @patch('{src}.InvalidationsManager'.format(**PATH))
    @patch('{src}.ContinuousProfiler'.format(**PATH))
    @patch('{src}.WorkerManager'.format(**PATH))
    @patch('{src}.load_config_override'.format(**PATH))
    @patch('{src}.loadPlugins'.format(**PATH))
    @patch('{src}.load_config'.format(**PATH))
    @patch('{src}.super'.format(**PATH))
    def test___init__(
        t, super, load_config, loadPlugins, load_config_override,
        WorkerManager, ContinuousProfiler, InvalidationsManager, MetricManager,
        signal,
    ):
        # Mock out setup methods with too many side-effects
        t.zenhub_patchers = [
            patch.object(ZenHub, 'notify_will_be_created', autospec=True),
            patch.object(ZenHub, '_getConf', autospec=True),
            patch.object(ZenHub, '_setup_pb_daemon', autospec=True),
        ]
        for patcher in t.zenhub_patchers:
            patcher.start()
            t.addCleanup(patcher.stop)

        # Attributes set by parent class
        ZenHub.options = sentinel.options
        ZenHub.options.profiling = sentinel.profiling
        ZenHub.options.invalidation_poll_interval = sentinel.inval_poll
        ZenHub.options.monitor = sentinel.monitor
        ZenHub.log = Mock(name='log', set_spec=[])
        ZenHub.dmd = Mock(name='dmd', set_spec=[])
        ZenHub.storage = Mock(name='storage', set_spec=['poll_invalidations'])

        zh = ZenHub()

        zh.notify_will_be_created.assert_called_with(zh)
        # Run parent class __init__
        super.assert_called_with(ZenHub, zh)
        loadPlugins.assert_called_with(zh.dmd)
        t.assertEqual(zh.workList, zh._worker_manager.work_list)
        ContinuousProfiler.assert_called_with('zenhub', log=zh.log)
        ContinuousProfiler.return_value.start.assert_called_with()
        InvalidationsManager.assert_called_with(
            zh.dmd,
            zh.log,
            zh.async_syncdb,
            zh.storage.poll_invalidations,
            zh.sendEvent,
            poll_interval=zh.options.invalidation_poll_interval,
        )
        t.assertEqual(
            zh._invalidations_manager, InvalidationsManager.return_value
        )
        MetricManager.assert_called_with(
            daemon_tags={
                'zenoss_daemon': 'zenhub',
                'zenoss_monitor': zh.options.monitor,
                'internal': True
            }
        )
        t.assertEqual(zh._metric_manager, MetricManager.return_value)
        zh._setup_pb_daemon.assert_called_with(zh)


class ZenHubTest(TestCase):

    def setUp(t):
        # Patch out the ZenHub __init__ method, due to excessive side-effects
        # TODO: use the init method with external side-effects patched out
        t.init_patcher = patch.object(
            ZenHub, '__init__', autospec=True, return_value=None
        )
        t.init_patcher.start()
        t.addCleanup(t.init_patcher.stop)

        t.time_patcher = patch('{src}.time'.format(**PATH), autospec=True)
        t.time = t.time_patcher.start()
        t.addCleanup(t.time_patcher.stop)
        t.reactor_patcher = patch(
            '{src}.reactor'.format(**PATH), autospec=True
        )
        t.reactor = t.reactor_patcher.start()
        t.addCleanup(t.reactor_patcher.stop)
        t.wm_patcher = patch(
            '{src}.WorkerManager'.format(**PATH), autospec=True
        )
        t.WorkerManager = t.wm_patcher.start()
        t.addCleanup(t.wm_patcher.stop)
        ZenHub.options = sentinel.options

        t.zh = ZenHub()
        # Set attributes that should be created by __init__
        t.zh.log = Mock(name='log', spec_set=['debug', 'warn', 'exception', 'warning'])
        t.zh.shutdown = False
        t.zh.zem = Mock(name='ZenEventManager', spec_set=['sendEvent'])

        t.zh.dmd = Mock(
            name='dmd', spec_set=['getPhysicalRoot', '_invalidation_filters']
        )
        t.zh.storage = Mock(name='storage', spec_set=['poll_invalidations'])
        t.zh._invalidations_manager = Mock(
            InvalidationsManager, name='InvalidationsManager'
        )
        t.zh.options = sentinel.options
        t.zh._worker_manager = t.WorkerManager(t.zh.getService, t.zh.options)

    @patch('{src}.HubWillBeCreatedEvent'.format(**PATH), autospec=True)
    @patch('{src}.notify'.format(**PATH), autospec=True)
    def test_notify_will_be_created(t, notify, HubWillBeCreatedEvent):
        t.zh.notify_will_be_created()
        notify.assert_called_with(HubWillBeCreatedEvent.return_value)
        HubWillBeCreatedEvent.assert_called_with(t.zh)

    @patch('{src}.HubCreatedEvent'.format(**PATH), autospec=True)
    @patch('{src}.notify'.format(**PATH), autospec=True)
    def test_notify_hub_created(t, notify, HubCreatedEvent):
        t.zh.notify_hub_created()
        notify.assert_called_with(HubCreatedEvent.return_value)
        HubCreatedEvent.assert_called_with(t.zh)

    @patch('{src}.ipv6_available'.format(**PATH), autospec=True)
    @patch('{src}.AuthXmlRpcService'.format(**PATH), autospec=True)
    @patch('{src}.server'.format(**PATH), autospec=True)
    @patch('{src}.portal'.format(**PATH), autospec=True)
    @patch('{src}.pb'.format(**PATH), autospec=True)
    @patch('{src}.HubRealm'.format(**PATH), autospec=True)
    def test__setup_pb_daemon(
        t, HubRealm, pb, portal, server, AuthXmlRpcService, ipv6_available
    ):
        t.zh.options = sentinel.options
        t.zh.options.pbport = sentinel.pbport
        t.zh.options.xmlrpcport = sentinel.xmlrpcport
        t.zh.loadChecker = create_autospec(t.zh.loadChecker)
        t.zh.setKeepAlive = create_autospec(t.zh.setKeepAlive)
        ipv6_available.return_value = False

        t.zh._setup_pb_daemon()

        HubRealm.assert_called_with(t.zh)
        t.zh.setKeepAlive.assert_called_with(
            t.reactor.listenTCP.return_value.socket
        )
        pb.PBServerFactory.assert_called_with(portal.Portal.return_value)
        AuthXmlRpcService.assert_called_with(
            t.zh.dmd, t.zh.loadChecker.return_value
        )
        server.Site.assert_called_with(AuthXmlRpcService.return_value)
        t.reactor.listenTCP.assert_has_calls([
            call(
                t.zh.options.pbport,
                pb.PBServerFactory.return_value,
                interface=''
            ),
            call(
                t.zh.options.xmlrpcport,
                server.Site.return_value,
                interface=''
            )
        ])

    def test_setKeepAlive(t):
        '''ConnectionHandler function
        '''
        socket = Mock(
            name='socket',
            spec_set=[
                'SOL_SOCKET', 'SO_KEEPALIVE', 'SOL_TCP',
                'TCP_KEEPIDLE', 'TCP_KEEPINTVL', 'TCP_KEEPCNT'
            ]
        )
        sock = Mock(name='sock', spec_set=['setsockopt', 'getsockname'])
        # Super Hacky patch to deal with internal import
        with patch.dict('sys.modules', socket=socket):
            t.zh.setKeepAlive(sock)
        # validate side effects: sock opts set as expected
        interval = max(CONNECT_TIMEOUT / 4, 10)
        sock.setsockopt.assert_has_calls([
            call(socket.SOL_SOCKET, socket.SO_KEEPALIVE, OPTION_STATE),
            call(socket.SOL_TCP, socket.TCP_KEEPIDLE, CONNECT_TIMEOUT),
            call(socket.SOL_TCP, socket.TCP_KEEPINTVL, interval),
            call(socket.SOL_TCP, socket.TCP_KEEPCNT, 2)
        ])

    def test_sighandler_USR2(t):
        t.zh.sighandler_USR2(signum='unused', frame='unused')
        t.zh._worker_manager._workerStats.assert_called_with()

    @patch('{src}.super'.format(**PATH))
    def test_sighandler_USR1(t, super):
        t.zh.profiler = Mock(name='profiler', spec_set=['dump_stats'])
        t.zh.options.profiling = True
        signum, frame = sentinel.signum, sentinel.frame

        ZenHub.sighandler_USR1(t.zh, signum=signum, frame=frame)

        t.zh.profiler.dump_stats.assert_called_with()
        super.assert_called_with(ZenHub, t.zh)
        super.return_value.sighandler_USR1.assert_called_with(
            signum, frame
        )

    @patch('{src}.getUtility'.format(**PATH), autospec=True)
    @patch('{src}.task.LoopingCall'.format(**PATH), autospec=True)
    def test_main(t, LoopingCall, getUtility):
        '''Daemon Entry Point
        Execution waits at reactor.run() until the reactor stops
        '''
        t.zh.options = sentinel.options
        t.zh.options.monitor = 'localhost'
        t.zh.options.cycle = True
        t.zh.options.profiling = True
        t.zh.profiler = Mock(name='profiler', spec_set=['stop'])
        t.zh._metric_manager = Mock(MetricManager)
        t.zh._setup_pb_daemon = create_autospec(t.zh._setup_pb_daemon)
        t.zh.notify_hub_created = create_autospec(t.zh.notify_hub_created)
        t.zh.sendEvent = create_autospec(t.zh.sendEvent)

        t.zh.main()

        # start heartbeat LoopingCall
        LoopingCall.assert_any_call(t.zh.heartbeat)
        t.zh.heartbeat_task.start.assert_any_call(30)
        # starts its metricreporter
        t.assertEqual(t.zh.metricreporter, t.zh._metric_manager.metricreporter)
        t.zh._metric_manager.start.assert_called_with()
        # trigger to shut down metric reporter before zenhub exits
        t.reactor.addSystemEventTrigger.assert_called_with(
            'before', 'shutdown', t.zh._metric_manager.stop
        )
        # Start the Invalidation Processor
        t.assertEqual(
            t.zh.process_invalidations_task, LoopingCall.return_value
        )
        LoopingCall.assert_called_with(
            t.zh._invalidations_manager.process_invalidations
        )
        t.zh.process_invalidations_task.start.assert_called_with(
            t.zh.options.invalidation_poll_interval
        )

        # After the reactor stops:
        t.zh.profiler.stop.assert_called_with()
        # Closes IEventPublisher, which breaks old integration tests
        getUtility.assert_called_with(IEventPublisher)
        getUtility.return_value.close.assert_called_with()

    def test_stop(t):
        t.assertFalse(t.zh.shutdown)
        t.zh.stop()
        t.assertTrue(t.zh.shutdown)

    @patch('{src}.IHubConfProvider'.format(**PATH), autospec=True)
    def test__getConf(t, IHubConfProvider):
        ret = t.zh._getConf()
        confProvider = IHubConfProvider.return_value
        t.assertEqual(ret, confProvider.getHubConf.return_value)

    @patch('{src}.MetricManager'.format(**PATH), autospec=True)
    def test_getRRDStats(t, MetricManager):
        t.zh._metric_manager = MetricManager.return_value
        t.zh._getConf = create_autospec(t.zh._getConf)

        ret = t.zh.getRRDStats()

        t.zh._metric_manager.get_rrd_stats.assert_called_with(
            t.zh._getConf(), t.zh.zem.sendEvent
        )
        t.assertEqual(ret, t.zh._metric_manager.get_rrd_stats.return_value)

    def test_processQueue(t):
        t.zh.processQueue()
        t.zh._invalidations_manager.process_invalidations.assert_called_with()

    def test__initialize_invalidation_filters(t):
        t.zh._initialize_invalidation_filters()
        t.zh._invalidations_manager\
            .initialize_invalidation_filters.assert_called_with()

    def test__filter_oids(t):
        oids = sentinel.oids
        t.zh._filter_oids(oids)
        t.zh._invalidations_manager._filter_oids.assert_called_with(oids)

    def test__transformOid(t):
        ret = t.zh._transformOid('oid', sentinel.obj)
        t.zh._invalidations_manager._transformOid.assert_called_with(
            'oid', sentinel.obj
        )
        t.assertEqual(
            ret, t.zh._invalidations_manager._transformOid()
        )

    def test_doProcessQueue(t):
        t.zh.doProcessQueue()
        t.zh._invalidations_manager._doProcessQueue.assert_called_with()

    @patch('{src}.Event'.format(**PATH), autospec=True)
    def test_sendEvent(t, Event):
        '''Event Management.  send events to the EventManager
        '''
        event = {'device': 'x', 'component': 'y', 'summary': 'msg'}

        t.zh.sendEvent(**event)

        Event.assert_called_with(**event)
        t.zh.zem.sendEvent.assert_called_with(Event.return_value)

    @patch('{src}.Event'.format(**PATH), autospec=True)
    def test_sendEvent_defaults(t, Event):
        t.zh.options = Mock(name='options', spec_set=['monitor'])

        t.zh.sendEvent(eventClass='class', summary='something', severity=0)

        Event.assert_called_with(
            device=t.zh.options.monitor,
            component=t.zh.name,
            eventClass='class',
            summary='something',
            severity=0,
        )
        t.zh.zem.sendEvent.assert_called_with(Event.return_value)

    # AttributeError: Mock object has no attribute '_loadCrendentials'
    @patch('{src}.checkers'.format(**PATH), spec=True)
    def test_loadChecker(t, checkers):
        t.zh.options = Mock(name='options', spec_set=['passwordfile'])
        checker = checkers.FilePasswordDB.return_value
        loaded = checker._loadCredentials.return_value
        loaded.next.return_value = ('usr', 'pas')

        ret = t.zh.loadChecker()

        checkers.FilePasswordDB.assert_called_with(t.zh.options.passwordfile)
        t.assertEqual(ret, checkers.FilePasswordDB.return_value)
        t.assertEqual(t.zh.workerUsername, 'usr')
        t.assertEqual(t.zh.workerPassword, 'pas')

    def test_getService(t):
        t.zh.dmd = Mock(name='dmd', spec_set=['Monitors'])
        name = 'module.name'
        instance = 'collector_instance'
        service = sentinel.service
        t.zh.dmd.Monitors.Performance._getOb.return_value = True
        t.zh.services = {(name, instance): service}

        ret = t.zh.getService(name, instance)

        t.assertEqual(ret, service)

    def test_getService_raises_RemoteBadMonitor(t):
        '''raises RemoteBadMonitor on invalid instance argument
        '''
        t.zh.dmd = Mock(name='dmd', spec_set=['Monitors'])
        t.zh.dmd.Monitors.Performance._getOb.return_value = False

        with t.assertRaises(RemoteBadMonitor):
            t.zh.getService('name', 'instance')

    def test_getService_cache_miss(t):
        t.zh.dmd = Mock(name='dmd', spec_set=['Monitors'])
        name = 'module.name'
        instance = 'collector_instance'
        service = sentinel.service
        t.zh.dmd.Monitors.Performance._getOb.return_value = True
        t.zh.services = {}

        # patch the internal import
        # from Products.ZenUtils.Utils import importClass
        Utils = MagicMock(
            name='Products.ZenUtils.Utils', spec_set=['importClass']
        )
        from Products.ZenUtils.Utils import importClass
        Utils.importClass = create_autospec(importClass, name='importClass')
        Utils.importClass.return_value.return_value = service
        modules = {'Products.ZenUtils.Utils': Utils}
        with patch.dict('sys.modules', modules):
            ret = t.zh.getService(name, instance)

        t.assertEqual(ret, service)

    @patch('{src}.WorkerInterceptor'.format(**PATH), autospec=True)
    def test_getService_forwarded_to_WorkerInterceptor(t, WorkerInterceptor):
        t.zh.dmd = Mock(name='dmd', spec_set=['Monitors'])
        name = 'module.name'
        instance = 'collector_instance'
        service = sentinel.service
        interceptor_service = sentinel.interceptor_service
        t.zh.dmd.Monitors.Performance._getOb.return_value = True
        t.zh.services = {}
        WorkerInterceptor.return_value = interceptor_service

        # patch the internal import
        # from Products.ZenUtils.Utils import importClass
        Utils = MagicMock(
            name='Products.ZenUtils.Utils', spec_set=['importClass']
        )
        from Products.ZenUtils.Utils import importClass
        Utils.importClass = create_autospec(importClass, name='importClass')
        Utils.importClass.return_value.return_value = service
        modules = {'Products.ZenUtils.Utils': Utils}
        with patch.dict('sys.modules', modules):
            ret = t.zh.getService(name, instance)

        WorkerInterceptor.assert_called_with(t.zh, service)
        t.assertEqual(ret, service)
        t.assertEqual(t.zh.services[name, instance], interceptor_service)

    def test_deferToWorker(t):
        args = (sentinel.arg0, sentinel.arg1)

        ret = t.zh.deferToWorker('svcName', 'instance', 'method', args)

        t.zh._worker_manager.defer_to_worker.assert_called_with(
            'svcName', 'instance', 'method', args
        )
        t.assertEqual(ret, t.zh._worker_manager.defer_to_worker.return_value)

    def test_updateStatusAtStart(t):
        wId = sentinel.worker_id
        job = Mock(name='job', spec_set=['instance', 'servicename', 'method'])

        t.zh.updateStatusAtStart(wId, job)

        t.zh._worker_manager.updateStatusAtStart.assert_called_with(wId, job)

    def test_updateStatusAtFinish(t):
        '''Worker Management Metric reporting function
        '''
        wId = sentinel.worker_id
        job = Mock(name='job', spec_set=['instance', 'servicename', 'method'])

        t.zh.updateStatusAtFinish(wId, job)

        t.zh._worker_manager.updateStatusAtFinish.assert_called_with(
            wId, job, error=None
        )

    def test_finished(t):
        '''Worker Management Function
        '''
        job = Mock(
            name='job', spec_set=['deferred'],
            deferred=Mock(defer.Deferred, name='deferred', autospec=True)
        )
        result = Mock(name='result', spec_set=['returnvalue'])
        finishedWorker = sentinel.zenhub_worker
        wId = sentinel.worker_id

        ret = t.zh.finished(job, result, finishedWorker, wId)

        t.zh._worker_manager.finished.assert_called_with(
            job, result, finishedWorker, wId
        )
        t.assertEqual(ret.result, t.zh._worker_manager.finished.return_value)

    def test_giveWorkToWorkers(t):
        '''Worker Management Function
        '''
        t.zh._worker_manager = Mock(WorkerManager)
        t.zh.giveWorkToWorkers()
        t.zh._worker_manager.giveWorkToWorkers.assert_called_with(
            requeue=False
        )

    def test__workerStats(t):
        '''Worker Status Logging
        sends status details for a worker to log output
        not testing log output formatting at this time
        '''
        t.zh._workerStats()
        t.zh._worker_manager._workerStats.assert_called_with()

    @patch('{src}.IHubHeartBeatCheck'.format(**PATH), autospec=True)
    @patch('{src}.EventHeartbeat'.format(**PATH), autospec=True)
    def test_heartbeat(t, EventHeartbeat, IHubHeartBeatCheck):
        '''Event Management / Daemon Function
        Also, some Metrics Reporting stuff for fun
        '''
        t.zh.options = Mock(
            name='options', spec_set=['monitor', 'name', 'heartbeatTimeout'],
        )
        t.zh.niceDoggie = create_autospec(t.zh.niceDoggie)
        t.zh._invalidations_manager = sentinel._invalidations_manager
        t.zh._invalidations_manager.totalTime = 100
        t.zh._invalidations_manager.totalEvents = 20
        # static value defined in function
        seconds = 30
        # Metrics reporting portion needs to be factored out
        t.zh.rrdStats = Mock(name='rrdStats', spec_set=['counter', 'gauge'])
        t.zh.totalTime = 1
        t.zh.totalEvents = sentinel.totalEvents
        service0 = Mock(name='service0', spec_set=['callTime'], callTime=9)
        t.zh.services = {'service0': service0}
        t.zh.workList = [sentinel.work0, sentinel.work1]
        t.zh.counters = collections.Counter()

        t.zh.heartbeat()

        EventHeartbeat.assert_called_with(
            t.zh.options.monitor, t.zh.name, t.zh.options.heartbeatTimeout
        )
        t.zh.zem.sendEvent.assert_called_with(EventHeartbeat.return_value)
        t.zh.niceDoggie.assert_called_with(seconds)
        IHubHeartBeatCheck.assert_called_with(t.zh)
        IHubHeartBeatCheck.return_value.check.assert_called_with()
        # Metrics reporting, copies zenhub.counters into rrdStats.counter
        t.zh.rrdStats.counter.has_calls([
            call('totalTime', int(t.zh.totalTime * 1000)),
            call('totalEvents', t.zh.totalEvents),
            call(
                'totalCallTime',
                sum(s.callTime for s in t.zh.services.values())
            ),
        ])
        t.zh.rrdStats.gauge.assert_has_calls([
            call('services', len(t.zh.services)),
            call('workListLength', len(t.zh.workList)),
        ])

    @patch('{src}.ParserReadyForOptionsEvent'.format(**PATH), autospec=True)
    @patch('{src}.notify'.format(**PATH), autospec=True)
    @patch('{src}.zenPath'.format(**PATH))
    @patch('{src}.ZCmdBase'.format(**PATH))
    def test_buildOptions(
        t, ZCmdBase, zenPath, notify, ParserReadyForOptionsEvent
    ):
        '''After initialization, the ZenHub instance should have
        options parsed from its buildOptions method
        assertions based on default options
        '''
        # this should call buildOptions on parent classes, up the tree
        # currently calls an ancestor class directly
        # parser expected to be added by CmdBase.buildParser
        from optparse import OptionParser
        t.zh.parser = OptionParser()

        t.zh.buildOptions()
        t.zh.options, args = t.zh.parser.parse_args()

        ZCmdBase.buildOptions.assert_called_with(t.zh)
        t.assertEqual(t.zh.options.xmlrpcport, XML_RPC_PORT)
        t.assertEqual(t.zh.options.pbport, PB_PORT)
        zenPath.assert_called_with('etc', 'hubpasswd')
        t.assertEqual(t.zh.options.passwordfile, zenPath.return_value)
        t.assertEqual(t.zh.options.monitor, 'localhost')
        t.assertEqual(t.zh.options.prioritize, False)
        t.assertEqual(t.zh.options.workersReservedForEvents, 1)
        t.assertEqual(t.zh.options.invalidation_poll_interval, 30)
        t.assertEqual(t.zh.options.profiling, False)
        t.assertEqual(t.zh.options.modeling_pause_timeout, 3600)
        # delay before actually parsing the options
        notify.assert_called_with(ParserReadyForOptionsEvent(t.zh.parser))


class HubAvitarTest(TestCase):

    def setUp(t):
        t.hub = Mock(
            name='hub',
            spec_set=['getService', 'log', 'workers', 'updateEventWorkerCount']
        )
        t.avitar = HubAvitar(t.hub)

    def test___init__(t):
        t.assertEqual(t.avitar.hub, t.hub)

    def test_perspective_ping(t):
        ret = t.avitar.perspective_ping()
        t.assertEqual(ret, 'pong')

    @patch('{src}.os.environ'.format(**PATH), name='os.environ', autospec=True)
    def test_perspective_getHubInstanceId(t, os_environ):
        ret = t.avitar.perspective_getHubInstanceId()
        os_environ.get.assert_called_with(
            'CONTROLPLANE_INSTANCE_ID', 'Unknown'
        )
        t.assertEqual(ret, os_environ.get.return_value)

    def test_perspective_getService(t):
        service_name = 'serviceName'
        instance = 'collector_instance_name'
        listener = sentinel.listener
        options = sentinel.options
        service = t.hub.getService.return_value

        ret = t.avitar.perspective_getService(
            service_name, instance=instance,
            listener=listener, options=options
        )

        t.hub.getService.assert_called_with(service_name, instance)
        service.addListener.assert_called_with(listener, options)
        t.assertEqual(ret, service)

    def test_perspective_getService_raises_RemoteBadMonitor(t):
        t.hub.getService.side_effect = RemoteBadMonitor('tb', 'msg')
        with t.assertRaises(RemoteBadMonitor):
            t.avitar.perspective_getService('service_name')

    def test_perspective_reportingForWork(t):
        worker = Mock(pb.RemoteReference, autospec=True)
        workerId = 0
        t.hub.workers = []

        t.avitar.perspective_reportingForWork(worker, workerId=workerId)

        t.assertFalse(worker.busy)
        t.assertEqual(worker.workerId, workerId)
        t.assertIn(worker, t.hub.workers)

        # Ugly test for the notifyOnDisconnect method, please refactor
        args, kwargs = worker.notifyOnDisconnect.call_args
        removeWorker = args[0]

        removeWorker(worker)
        t.assertNotIn(worker, t.hub.workers)


class WorkerManagerTest(TestCase):

    def setUp(t):
        t.selector_patcher = patch(
            '{src}.WorkerSelector'.format(**PATH), autospec=True
        )
        t.selector_patcher.start()
        t.addCleanup(t.selector_patcher.stop)

        t.reactor_patcher = patch(
            '{src}.reactor'.format(**PATH), autospec=True
        )
        t.reactor = t.reactor_patcher.start()
        t.addCleanup(t.reactor_patcher.stop)

        t.getService = Mock(ZenHub.getService)
        t.zenhub_options = sentinel.zenhub_options
        t.wm = WorkerManager(t.getService, t.zenhub_options)

    def test___init__(t):
        t.assertEqual(t.wm._get_service, t.getService)
        t.assertIsInstance(t.wm._worker_selector, WorkerSelector)
        t.assertEqual(t.wm.workers, [])

    @patch('{src}.time'.format(**PATH), autospec=True)
    @patch('{src}.defer'.format(**PATH), autospec=True)
    @patch('{src}.HubWorklistItem'.format(**PATH), autospec=True)
    def test_defer_to_worker(t, HubWorklistItem, defer, time):
        '''should be refactored to use inlineCallbacks
        '''
        service = t.getService.return_value.service
        args = (sentinel.arg0, sentinel.arg1)

        ret = t.wm.defer_to_worker('svcName', 'instance', 'method', args)

        HubWorklistItem.assert_called_with(
            service.getMethodPriority.return_value,
            time.time.return_value,
            defer.Deferred.return_value,
            'svcName', 'instance', 'method',
            ('svcName', 'instance', 'method', args),
        )
        t.reactor.callLater.assert_called_with(0, t.wm.giveWorkToWorkers)
        t.assertEqual(ret, defer.Deferred.return_value)

    def test_giveWorkToWorkers(t):
        t.wm.dmd = Mock(name='dmd', spec_set=['getPauseADMLife'])
        t.wm.dmd.getPauseADMLife.return_value = 1
        t.wm.options = Mock(
            name='options', spec_set=['modeling_pause_timeout']
        )
        t.wm.options.modeling_pause_timeout = 0
        job = Mock(name='job', spec_set=['method', 'args'])
        job.args = [sentinel.arg0, sentinel.arg1]
        t.wm.work_list.append(job)
        worker = Mock(
            name='worker', spec_set=['busy', 'callRemote'], busy=False
        )
        worker.callRemote.return_value = sentinel.result
        t.wm._workers = [worker]
        t.wm.workerselector = Mock(
            name='WorkerSelector', spec_set=['getCandidateWorkerIds']
        )
        t.wm.workerselector.getCandidateWorkerIds.return_value = [0]
        t.wm.counters = {'workerItems': 0}
        t.wm.updateStatusAtStart = create_autospec(t.wm.updateStatusAtStart)
        t.wm.finished = create_autospec(t.wm.finished)

        t.wm.giveWorkToWorkers()

        t.wm.workerselector.getCandidateWorkerIds.assert_called_with(
            job.method, [worker]
        )
        worker.callRemote.assert_called_with('execute', *job.args)
        t.wm.finished.assert_called_with(
            job, worker.callRemote.return_value, worker, 0
        )

    @patch('{src}.time'.format(**PATH), autospec=True)
    @patch('{src}.WorkerStats'.format(**PATH), autospec=True)
    def test_updateStatusAtStart(t, WorkerStats, time):
        '''Worker Management Metric reporting function'''
        wId = sentinel.worker_id
        job = Mock(name='job', spec_set=['instance', 'servicename', 'method'])

        t.wm.updateStatusAtStart(wId, job)

        t.assertEqual(
            t.wm.executionTimer, {job.method: [1, 0.0, 0.0, time.time()]}
        )
        WorkerStats.assert_called_with(
            'Busy',
            "%s:%s.%s" % (job.instance, job.servicename, job.method),
            time.time(),
            0
        )
        t.assertEqual(t.wm.workTracker[wId], WorkerStats.return_value)

    @patch('{src}.time'.format(**PATH), autospec=True)
    @patch('{src}.WorkerStats'.format(**PATH), autospec=True)
    def test_updateStatusAtFinish(t, WorkerStats, time):
        '''Worker Management Metric reporting function
        '''
        # this should be set by __init__, not specified here
        t.wm.executionTimer = collections.defaultdict(lambda: [0, 0.0, 0.0, 0])
        wId = sentinel.worker_id
        t0, t1 = 100, 300
        stats = Mock(
            name='stats', spec_set=['lastupdate', 'description'], lastupdate=t0
        )
        time.time.return_value = t1
        t.wm.workTracker = {wId: stats}
        job = Mock(name='job', spec_set=['instance', 'servicename', 'method'])

        t.wm.updateStatusAtFinish(wId, job)

        t.assertEqual(
            t.wm.executionTimer, {job.method: [0, 0.0, t1 - t0, t1]},
        )
        WorkerStats.assert_called_with('Idle', stats.description, t1, 0)
        t.assertEqual(t.wm.workTracker[wId], WorkerStats.return_value)

    def test_finished(t):
        '''Worker Management Function
        '''
        t.wm.updateStatusAtFinish = create_autospec(t.wm.updateStatusAtFinish)
        job = Mock(
            name='job', spec_set=['deferred'],
            deferred=Mock(defer.Deferred, name='deferred', autospec=True)
        )
        result = Mock(name='result', spec_set=['returnvalue'])
        finishedWorker = sentinel.zenhub_worker
        wId = sentinel.worker_id

        ret = t.wm.finished(job, result, finishedWorker, wId)

        job.deferred.callback.assert_called_with(result)
        # WARNING: may be called with error from pickle.loads, or ''.join
        # this should be
        # t.wm.updateStatusAtFinish.assert_called_with(wId, job, None)
        # Hack to test called_with manually
        args, kwargs = t.wm.updateStatusAtFinish.call_args
        t.assertEqual(args[0], wId)
        t.assertEqual(args[1], job)
        t.assertIsInstance(args[2], TypeError)

        t.assertIsInstance(ret, defer.Deferred)
        t.assertEqual(ret.result, result)
        t.assertFalse(finishedWorker.busy)
        t.reactor.callLater.assert_called_with(0.1, t.wm.giveWorkToWorkers)

    def test_finished_handles_LastCallReturnValue(t):
        t.wm.updateStatusAtFinish = create_autospec(t.wm.updateStatusAtFinish)
        job = Mock(
            name='job', spec_set=['deferred'],
            deferred=Mock(defer.Deferred, name='deferred', autospec=True)
        )
        result = Mock(LastCallReturnValue, name='result')
        t.assertIsInstance(result, LastCallReturnValue)
        finishedWorker = sentinel.zenhub_worker
        wId = sentinel.worker_id
        t.wm._workers = [finishedWorker, 'other worker']

        ret = t.wm.finished(job, result, finishedWorker, wId)

        t.assertNotIn(finishedWorker, t.wm.workers)
        t.assertEqual(ret.result, result.returnvalue)

    def test_workerStats(t):
        '''Worker Status Logging
        sends status details for workers to log output
        not testing log output formatting at this time
        '''
        t.wm._workerStats()


class _ZenHubWorklistTest(TestCase):

    def setUp(t):
        t.wl = _ZenHubWorklist()

    def test____init__(t):
        t.assertEqual(
            t.wl.eventPriorityList,
            [t.wl.eventworklist, t.wl.otherworklist, t.wl.applyworklist]
        )
        t.assertEqual(
            t.wl.otherPriorityList,
            [t.wl.otherworklist, t.wl.applyworklist, t.wl.eventworklist]
        )
        t.assertEqual(
            t.wl.applyPriorityList,
            [t.wl.applyworklist, t.wl.eventworklist, t.wl.otherworklist]
        )
        t.assertEqual(
            t.wl.dispatch,
            {
                'sendEvents': t.wl.eventworklist,
                'sendEvent': t.wl.eventworklist,
                'applyDataMaps': t.wl.applyworklist
            }
        )

    def test___getitem__(t):
        '''zenhub_worker_list[dispatch] uses the dispatch dict to
        map 'sendEvents', 'sendEvent', 'applyDataMaps' keys to worklists
        '''
        t.assertEqual(t.wl['sendEvents'], t.wl.eventworklist)
        t.assertEqual(t.wl['sendEvent'], t.wl.eventworklist)
        t.assertEqual(t.wl['applyDataMaps'], t.wl.applyworklist)
        t.assertEqual(t.wl['anything else'], t.wl.otherworklist)

    def test___len__(t):
        '''len(zenhub_worker_list) returns the sum of all work lists
        '''
        t.wl.eventworklist = range(1)
        t.wl.applyworklist = range(2)
        t.wl.otherworklist = range(4)
        t.assertEqual(len(t.wl), 7)

    def test_push(t):
        other = Mock(
            name='apply_datamap', spec_set=['method'], method='other'
        )
        t.wl.push(other)
        t.assertEqual(t.wl.otherworklist, [other])

    def test_push_sendEvent(t):
        send_event = Mock(
            name='send_event', spec_set=['method'], method='sendEvent'
        )
        t.wl.push(send_event)
        t.assertEqual(t.wl['sendEvent'], [send_event])

    def test_push_sendEvents(t):
        send_events = Mock(
            name='send_events', spec_set=['method'], method='sendEvents'
        )
        t.wl.push(send_events)
        t.assertEqual(t.wl['sendEvents'], [send_events])

    def test_push_applyDataMaps(t):
        apply_datamap = Mock(
            name='apply_datamap', spec_set=['method'], method='applyDataMaps'
        )
        t.wl.push(apply_datamap)
        t.assertEqual(t.wl['applyDataMaps'], [apply_datamap])

    def test_append(t):
        t.assertEqual(t.wl.append, t.wl.push)

    def test_pop(t):
        '''randomizes selection from lists in an attempt to weight and balance
        item selection. with an option to ignore the applyDataMaps queue.
        current implementation is highly inefficient.
        current logic will not apply weighing properly if allowADM=False.
        cannot set random.seed('static'), random was not imported

        Should be reviewed and refactored.
        '''
        job_a = Mock(name='job_a', spec_set=['method'], method='sendEvent')

        t.wl.push(job_a)

        ret = t.wl.pop()
        t.assertEqual(ret, job_a)
        ret = t.wl.pop()
        t.assertEqual(ret, None)

    @patch('{src}.ListLengthGauge'.format(**PATH), autospec=True)
    @patch('{src}.registry'.format(**PATH), autospec=True)
    @patch('{src}.Metrology'.format(**PATH), autospec=True)
    def test_configure_metrology(t, Metrology, registry, ListLengthGauge):
        t.wl.configure_metrology()

        # guages are registered with Metrology
        Metrology.gauge.assert_has_calls([
            call('zenhub.eventWorkList', ListLengthGauge.return_value),
            call('zenhub.admWorkList', ListLengthGauge.return_value),
            call('zenhub.otherWorkList', ListLengthGauge.return_value),
            call('zenhub.workList', ListLengthGauge.return_value),
        ])

        ListLengthGauge.assert_has_calls([
            call(t.wl.eventworklist),
            call(t.wl.applyworklist),
            call(t.wl.otherworklist),
            call(t.wl),
        ])


class ListLengthGaugeTest(TestCase):

    def test_value(t):
        _list = [i for i in range(3)]
        gauge = ListLengthGauge(_list)
        t.assertEqual(gauge.value, len(_list))

        _list += [i for i in range(4)]
        t.assertEqual(gauge.value, 7)


class AuthXmlRpcServiceTest(TestCase):

    def setUp(t):
        t.dmd = Mock(name='dmd', spec_set=['ZenEventManager'])
        t.checker = Mock(name='checker', spec_set=['requestAvatarId'])

        t.axrs = AuthXmlRpcService(t.dmd, t.checker)

    @patch('{src}.XmlRpcService.__init__'.format(**PATH), autospec=True)
    def test___init__(t, XmlRpcService__init__):
        dmd = sentinel.dmd
        checker = sentinel.checker

        axrs = AuthXmlRpcService(dmd, checker)

        XmlRpcService__init__.assert_called_with(axrs, dmd)
        t.assertEqual(axrs.checker, checker)

    def test_doRender(t):
        '''should be refactored to call self.render,
        instead of the parrent class directly
        '''
        render = create_autospec(XmlRpcService.render, name='render')
        XmlRpcService.render = render
        request = sentinel.request

        ret = t.axrs.doRender('unused arg', request)

        XmlRpcService.render.assert_called_with(t.axrs, request)
        t.assertEqual(ret, render.return_value)

    @patch('{src}.xmlrpc'.format(**PATH), name='xmlrpc', autospec=True)
    def test_unauthorized(t, xmlrpc):
        request = sentinel.request
        t.axrs._cbRender = create_autospec(t.axrs._cbRender)

        t.axrs.unauthorized(request)

        xmlrpc.Fault.assert_called_with(t.axrs.FAILURE, 'Unauthorized')
        t.axrs._cbRender.assert_called_with(xmlrpc.Fault.return_value, request)

    @patch('{src}.server'.format(**PATH), name='server', autospec=True)
    @patch(
        '{src}.credentials'.format(**PATH), name='credentials', autospec=True
    )
    def test_render(t, credentials, server):
        request = Mock(name='request', spec_set=['getHeader'])
        auth = Mock(name='auth', spec_set=['split'])
        encoded = Mock(name='encoded', spec_set=['decode'])
        encoded.decode.return_value.split.return_value = ('user', 'password')
        auth.split.return_value = ('Basic', encoded)

        request.getHeader.return_value = auth

        ret = t.axrs.render(request)

        request.getHeader.assert_called_with('authorization')
        encoded.decode.assert_called_with('base64')
        encoded.decode.return_value.split.assert_called_with(':')
        credentials.UsernamePassword.assert_called_with('user', 'password')
        t.axrs.checker.requestAvatarId.assert_called_with(
            credentials.UsernamePassword.return_value
        )
        deferred = t.axrs.checker.requestAvatarId.return_value
        deferred.addCallback.assert_called_with(t.axrs.doRender, request)

        t.assertEqual(ret, server.NOT_DONE_YET)


class MetricManagerTest(TestCase):

    def setUp(t):
        t.tmr_patcher = patch(
            '{src}.TwistedMetricReporter'.format(**PATH), autospec=True,
        )
        t.TwistedMetricReporter = t.tmr_patcher.start()
        t.addCleanup(t.tmr_patcher.stop)

        t.daemon_tags = {
            'zenoss_daemon': 'zenhub',
            'zenoss_monitor': 'localhost',
            'internal': True
        }

        t.mm = MetricManager(t.daemon_tags)

    def test___init__(t):
        t.assertEqual(t.mm.daemon_tags, t.daemon_tags)

    def test_start(t):
        t.mm.start()
        t.mm.metricreporter.start.assert_called_with()

    def test_stop(t):
        t.mm.stop()
        t.mm.metricreporter.stop.assert_called_with()

    def test_metric_reporter(t):
        t.assertEqual(
            t.mm.metricreporter, t.TwistedMetricReporter.return_value
        )
        t.TwistedMetricReporter.assert_called_with(
            metricWriter=t.mm.metric_writer, tags=t.mm.daemon_tags
        )

    @patch('{src}.BuiltInDS'.format(**PATH), autospec=True)
    @patch('{src}.DerivativeTracker'.format(**PATH), autospec=True)
    @patch('{src}.ThresholdNotifier'.format(**PATH), autospec=True)
    @patch('{src}.DaemonStats'.format(**PATH), autospec=True)
    def test_get_rrd_stats(
        t, DaemonStats, ThresholdNotifier, DerivativeTracker, BuiltInDS
    ):
        hub_config = Mock(
            name='hub_config', spec_set=['getThresholdInstances', 'id']
        )
        send_event = sentinel.send_event_function

        ret = t.mm.get_rrd_stats(hub_config, send_event)

        rrd_stats = DaemonStats.return_value
        thresholds = hub_config.getThresholdInstances.return_value
        threshold_notifier = ThresholdNotifier.return_value
        derivative_tracker = DerivativeTracker.return_value

        hub_config.getThresholdInstances.assert_called_with(
            BuiltInDS.sourcetype
        )
        ThresholdNotifier.assert_called_with(send_event, thresholds)

        rrd_stats.config.assert_called_with(
            'zenhub',
            hub_config.id,
            t.mm.metric_writer,
            threshold_notifier,
            derivative_tracker
        )

        t.assertEqual(ret, DaemonStats.return_value)

    @patch('{src}.os'.format(**PATH), autospec=True)
    @patch('{src}.redisPublisher'.format(**PATH), autospec=True)
    @patch('{src}.MetricWriter'.format(**PATH), autospec=True)
    def test_metric_writer(t, MetricWriter, redisPublisher, os):
        os.environ = {'CONTROLPLANE': '0'}

        ret = t.mm.metric_writer

        t.assertEqual(ret, MetricWriter.return_value)
        MetricWriter.assert_called_with(redisPublisher.return_value)

    @patch('{src}.AggregateMetricWriter'.format(**PATH), autospec=True)
    @patch('{src}.FilteredMetricWriter'.format(**PATH), autospec=True)
    @patch('{src}.publisher'.format(**PATH), autospec=True)
    @patch('{src}.os'.format(**PATH), autospec=True)
    def test__setup_cc_metric_writer(
        t, os, publisher, FilteredMetricWriter, AggregateMetricWriter
    ):
        usr, pas = 'consumer_username', 'consumer_password'
        internal_url = 'consumer_url'
        os.environ = {
            'CONTROLPLANE': '1',
            'CONTROLPLANE_CONSUMER_URL': internal_url,
            'CONTROLPLANE_CONSUMER_USERNAME': usr,
            'CONTROLPLANE_CONSUMER_PASSWORD': pas,
        }
        metric_writer = sentinel.metric_writer

        ret = t.mm._setup_cc_metric_writer(metric_writer)

        publisher.assert_called_with(usr, pas, internal_url)
        FilteredMetricWriter.assert_called_with(
            publisher.return_value, t.mm._internal_metric_filter
        )
        AggregateMetricWriter.assert_called_with(
            [metric_writer, FilteredMetricWriter.return_value]
        )
        t.assertEqual(ret, AggregateMetricWriter.return_value)

    def test_internal_metric_filter(t):
        tags = {'t1': True, 'internal': True}
        ret = t.mm._internal_metric_filter(
            sentinel.metric, sentinel.value, sentinel.timestamp, tags
        )
        t.assertEqual(ret, True)

    def test_internal_metric_filter_False(t):
        tags = {'t1': True, 'not internal': True}
        ret = t.mm._internal_metric_filter(
            sentinel.metric, sentinel.value, sentinel.timestamp, tags
        )
        t.assertEqual(ret, False)


class ZenHubModuleTest(TestCase):

    @patch('{src}.HttpPostPublisher'.format(**PATH), autospec=True)
    def test_publisher(t, HttpPostPublisher):
        ret = publisher('username', 'password', 'url')
        HttpPostPublisher.assert_called_with('username', 'password', 'url')
        t.assertEqual(ret, HttpPostPublisher.return_value)

    @patch('{src}.RedisListPublisher'.format(**PATH), autospec=True)
    def test_redisPublisher(t, RedisListPublisher):
        ret = redisPublisher()
        RedisListPublisher.assert_called_with()
        t.assertEqual(ret, RedisListPublisher.return_value)


class InvalidationsManagerTest(TestCase):

    def setUp(t):
        t.dmd = Mock(name='dmd', spec_set=['getPhysicalRoot'])
        t.log = Mock(name='log', spec_set=['debug', 'warn'])
        t.syncdb = Mock(name='ZenHub.async_syncdb', spec_set=[])
        t.poll_invalidations = Mock(
            name='ZenHub.storage.poll_invalidations', spec_set=[]
        )
        t.send_event = create_autospec(ZenHub.sendEvent)

        t.im = InvalidationsManager(
            t.dmd, t.log, t.syncdb, t.poll_invalidations, t.send_event
        )

    def test___init__(t):
        t.assertEqual(t.im._InvalidationsManager__dmd, t.dmd)
        t.assertEqual(t.im.log, t.log)
        t.assertEqual(t.im._InvalidationsManager__syncdb, t.syncdb)
        t.assertEqual(
            t.im._InvalidationsManager__poll_invalidations,
            t.poll_invalidations
        )
        t.assertEqual(t.im._InvalidationsManager__send_event, t.send_event)

        t.assertEqual(t.im._invalidations_paused, False)
        t.assertEqual(t.im.totalEvents, 0)
        t.assertEqual(t.im.totalTime, 0)

    @patch('{src}.getUtilitiesFor'.format(**PATH), autospec=True)
    def test_initialize_invalidation_filters(t, getUtilitiesFor):
        MockIInvalidationFilter = create_interface_mock(IInvalidationFilter)
        filters = [MockIInvalidationFilter() for i in range(3)]
        # weighted in reverse order
        for i, filter in enumerate(filters):
            filter.weight = 10 - i
        getUtilitiesFor.return_value = [
            ('f%s' % i, f) for i, f in enumerate(filters)
        ]

        t.im.initialize_invalidation_filters()

        for filter in filters:
            filter.initialize.assert_called_with(t.dmd)

        # check sorted by weight
        filters.reverse()
        t.assertEqual(t.im._invalidation_filters, filters)

    @patch('{src}.getUtility'.format(**PATH), autospec=True)
    @patch('{src}.time'.format(**PATH), autospec=True)
    def test_process_invalidations(t, time, getUtility):
        '''synchronize with the database, and poll invalidated oids from it,
        filter the oids,  send them to the invalidation_processor
        '''
        t.im._filter_oids = create_autospec(t.im._filter_oids)
        processor = getUtility.return_value
        timestamps = [10, 20]
        time.time.side_effect = timestamps

        t.im.process_invalidations()

        t.syncdb.assert_called_with()
        t.poll_invalidations.assert_called_with()
        getUtility.assert_called_with(IInvalidationProcessor)
        processor.processQueue.assert_called_with(
            tuple(set(t.im._filter_oids(t.poll_invalidations.return_value)))
        )

        t.assertEqual(t.im.totalTime, timestamps[1] - timestamps[0])
        t.assertEqual(t.im.totalEvents, 1)

    def test__syncdb(t):
        t.im._syncdb()
        t.syncdb.assert_called_with()

    def test_poll_invalidations(t):
        ret = t.im._poll_invalidations()
        t.assertEqual(ret, t.poll_invalidations.return_value)

    def test__filter_oids(t):
        '''Configuration Invalidation Processing function
        yields a generator with the OID if the object has been deleted
        runs changed devices through invalidation_filters
        which may exclude them,
        and runs any included devices through _transformOid
        '''
        app = t.dmd.getPhysicalRoot.return_value

        device = MagicMock(PrimaryPathObjectManager, __of__=Mock())
        device_obj = sentinel.device_obj
        device.__of__.return_value.primaryAq.return_value = device_obj
        component = MagicMock(DeviceComponent, __of__=Mock())
        component_obj = sentinel.component_obj
        component.__of__.return_value.primaryAq.return_value = component_obj
        excluded = Mock(DeviceComponent, __of__=Mock())
        excluded_obj = sentinel.excluded_obj
        excluded.__of__.return_value.primaryAq.return_value = excluded_obj
        excluded_type = Mock(name='ignored obj type', __of__=Mock())
        transformer = MagicMock(PrimaryPathObjectManager, __of__=Mock())
        transf_obj = sentinel.transformer
        transformer.__of__.return_value.primaryAq.return_value = transf_obj

        app._p_jar = {
            111: device,
            222: component,
            333: excluded,
            444: excluded_type,
            555: transformer,
        }
        oids = app._p_jar.keys()

        def include(obj):
            if obj in [device_obj, component_obj]:
                return FILTER_INCLUDE
            if obj is sentinel.transformer:
                return FILTER_INCLUDE
            if obj == excluded_obj:
                return FILTER_EXCLUDE

        MockIInvalidationFilter = create_interface_mock(IInvalidationFilter)
        filter = MockIInvalidationFilter()
        filter.include = include
        t.im._invalidation_filters = [filter]

        def transform_oid(oid, obj):
            if oid in [111, 222]:
                return (oid,)
            if oid == 555:
                return {888, 999}

        t.im._transformOid = transform_oid

        ret = t.im._filter_oids(oids)
        out = {o for o in ret}  # unwind the generator

        t.assertEqual(out, {111, 222, 888, 999})

    def test__filter_oids_deleted(t):
        app = t.dmd.getPhysicalRoot.return_value = MagicMock(name='root')
        app._p_jar.__getitem__.side_effect = POSKeyError()

        ret = t.im._filter_oids([111])
        out = [o for o in ret]  # unwind the generator
        t.assertEqual(out, [111])

    def test__filter_oids_deleted_primaryaq(t):
        deleted = MagicMock(DeviceComponent, __of__=Mock())
        deleted.__of__.return_value.primaryAq.side_effect = KeyError
        with t.assertRaises(KeyError):
            deleted.__of__().primaryAq()

        app = t.dmd.getPhysicalRoot.return_value
        app._p_jar = {111: deleted}

        ret = t.im._filter_oids([111])
        out = [o for o in ret]
        t.assertEqual(out, [111])

    def test__oid_to_object(t):
        device = MagicMock(PrimaryPathObjectManager, __of__=Mock())
        device_obj = sentinel.device_obj
        device.__of__.return_value.primaryAq.return_value = device_obj
        app = sentinel.dmd_root
        app._p_jar = {111: device}

        ret = t.im._oid_to_object(app, 111)

        t.assertEqual(ret, device_obj)

    def test__oid_to_object_poskeyerror(t):
        app = MagicMock(name='dmd.root', spec_set=['_p_jar'])
        app._p_jar.__getitem__.side_effect = POSKeyError()

        ret = t.im._oid_to_object(app, 111)

        t.assertEqual(ret, FILTER_INCLUDE)

    def test__oid_to_object_deleted_primaryaq_keyerror(t):
        deleted = MagicMock(DeviceComponent, __of__=Mock())
        deleted.__of__.return_value.primaryAq.side_effect = KeyError
        app = sentinel.dmd_root
        app._p_jar = {111: deleted}

        ret = t.im._oid_to_object(app, 111)

        t.assertEqual(ret, FILTER_INCLUDE)

    def test__oid_to_object_exclude_unsuported_types(t):
        unsuported = MagicMock(name='unsuported type', __of__=Mock())
        app = sentinel.dmd_root
        app._p_jar = {111: unsuported}

        ret = t.im._oid_to_object(app, 111)

        t.assertEqual(ret, FILTER_EXCLUDE)

    def test__apply_filters(t):
        MockIInvalidationFilter = create_interface_mock(IInvalidationFilter)
        filter = MockIInvalidationFilter()

        def include(obj):
            if obj is sentinel.included:
                return FILTER_INCLUDE
            elif obj is sentinel.excluded:
                return FILTER_EXCLUDE
            else:
                return "FILTER_CONTINUE"

        filter.include = include
        t.im._invalidation_filters = [filter]

        t.assertTrue(t.im._apply_filters(sentinel.included))
        t.assertFalse(t.im._apply_filters(sentinel.excluded))
        t.assertTrue(t.im._apply_filters(sentinel.other))

    @patch('{src}.IInvalidationOid'.format(**PATH), autospec=True)
    @patch('{src}.subscribers'.format(**PATH), autospec=True)
    def test__transformOid(t, subscribers, IInvalidationOid):
        '''Configuration Invalidation Processing function
        given an oid: object pair
        gets a list of transforms for the object
        executes the transforms given the oid
        returns a set of oids returned by the transforms
        '''
        adapter_a = Mock(
            name='adapter_a', spec_set=['transformOid'],
            transformOid=lambda x: x + '0'
        )
        subscribers.return_value = [adapter_a]
        adapter_b = Mock(
            name='adapter_b', spec_set=['transformOid'],
            transformOid=lambda x: [x + '1', x + '2']
        )
        IInvalidationOid.return_value = adapter_b
        oid = 'oid'
        obj = sentinel.object

        ret = t.im._transformOid(oid, obj)

        t.assertEqual(ret, {'oid0', 'oid1', 'oid2'})

    def test__send_event(t):
        t.im._send_event(sentinel.event)
        t.send_event.assert_called_with(sentinel.event)

    def test__send_invalidations_unpaused_event(t):
        t.im._send_invalidations_unpaused_event(sentinel.msg)
        t.send_event.assert_called_with({
            'summary': sentinel.msg,
            'severity': SEVERITY_CLEAR,
            'eventkey': INVALIDATIONS_PAUSED
        })

    @patch('{src}.getUtility'.format(**PATH), autospec=True)
    def test__doProcessQueue(t, getUtility):
        '''Configuration Invalidation Processing function
        pulls in a dict of invalidations, and the IInvalidationProcessor
        and processes them, then sends an event
        refactor to use inline callbacks
        '''
        # storage is ZODB access inherited from a parent class
        t.im._filter_oids = create_autospec(t.im._filter_oids)

        t.im._doProcessQueue()

        getUtility.assert_called_with(IInvalidationProcessor)
        getUtility.return_value.processQueue.assert_called_with(
            tuple(set(t.im._filter_oids.return_value))
        )


class DefaultConfProviderTest(TestCase):

    def test_implements_IHubConfProvider(t):
        # the class Implements the Interface
        t.assertTrue(IHubConfProvider.implementedBy(DefaultConfProvider))

    def test_adapts_ZenHub(t):
        t.assertEqual(
            adaptedBy(DefaultConfProvider), (ZenHub, )
        )
        t.assertIn(ZenHub, adaptedBy(DefaultConfProvider))

    def test___init__(t):
        zenhub = sentinel.zenhub

        default_conf_provider = DefaultConfProvider(zenhub)

        # the object provides the interface
        t.assertTrue(IHubConfProvider.providedBy(default_conf_provider))
        # Verify the object implments the interface properly
        verifyObject(IHubConfProvider, default_conf_provider)
        t.assertEqual(default_conf_provider._zenhub, zenhub)

    def test_getHubConf(t):
        zenhub = Mock(name='zenhub', spec_set=['dmd', 'options'])
        default_conf_provider = DefaultConfProvider(zenhub)

        ret = default_conf_provider.getHubConf()

        zenhub.dmd.Monitors.Performance._getOb.assert_called_with(
            zenhub.options.monitor, None
        )
        t.assertEqual(ret, zenhub.dmd.Monitors.Performance._getOb.return_value)


class DefaultHubHeartBeatCheckTest(TestCase):

    def test_implements_IHubHeartBeatCheck(t):
        # the class Implements the Interface
        t.assertTrue(
            IHubHeartBeatCheck.implementedBy(DefaultHubHeartBeatCheck)
        )

    def test_adapts_ZenHub(t):
        t.assertIn(ZenHub, adaptedBy(DefaultHubHeartBeatCheck))

    def test___init__(t):
        zenhub = sentinel.zenhub

        default_hub_heartbeat_check = DefaultHubHeartBeatCheck(zenhub)

        # the object provides the interface
        t.assertTrue(
            IHubHeartBeatCheck.providedBy(default_hub_heartbeat_check)
        )
        # Verify the object implments the interface properly
        verifyObject(IHubHeartBeatCheck, default_hub_heartbeat_check)
        t.assertEqual(default_hub_heartbeat_check._zenhub, zenhub)

    def test_check(t):
        # does nothing
        zenhub = sentinel.zenhub
        default_hub_heartbeat_check = DefaultHubHeartBeatCheck(zenhub)
        default_hub_heartbeat_check.check()


class ServiceAddedEventTest(TestCase):
    def test___init__(t):
        name, instance = 'name', 'instance'
        service_added_event = ServiceAddedEvent(name, instance)
        # the class Implements the Interface
        t.assertTrue(IServiceAddedEvent.implementedBy(ServiceAddedEvent))
        # the object provides the interface
        t.assertTrue(IServiceAddedEvent.providedBy(service_added_event))
        # Verify the object implments the interface properly
        verifyObject(IServiceAddedEvent, service_added_event)

        t.assertEqual(service_added_event.name, name)
        t.assertEqual(service_added_event.instance, instance)


class HubWillBeCreatedEventTest(TestCase):
    def test__init__(t):
        hub = sentinel.zenhub_instance
        event = HubWillBeCreatedEvent(hub)
        # the class Implements the Interface
        t.assertTrue(
            IHubWillBeCreatedEvent.implementedBy(HubWillBeCreatedEvent)
        )
        # the object provides the interface
        t.assertTrue(IHubWillBeCreatedEvent.providedBy(event))
        # Verify the object implments the interface properly
        verifyObject(IHubWillBeCreatedEvent, event)

        t.assertEqual(event.hub, hub)


class HubCreatedEventTest(TestCase):
    def test__init__(t):
        hub = sentinel.zenhub_instance
        event = HubCreatedEvent(hub)
        # the class Implements the Interface
        t.assertTrue(
            IHubCreatedEvent.implementedBy(HubCreatedEvent)
        )
        # the object provides the interface
        t.assertTrue(IHubCreatedEvent.providedBy(event))
        # Verify the object implments the interface properly
        verifyObject(IHubCreatedEvent, event)

        t.assertEqual(event.hub, hub)


class ParserReadyForOptionsEventTest(TestCase):
    def test__init__(t):
        parser = sentinel.parser
        event = ParserReadyForOptionsEvent(parser)
        # the class Implements the Interface
        t.assertTrue(
            IParserReadyForOptionsEvent.implementedBy(
                ParserReadyForOptionsEvent
            )
        )
        # the object provides the interface
        t.assertTrue(IParserReadyForOptionsEvent.providedBy(event))
        # Verify the object implments the interface properly
        verifyObject(IParserReadyForOptionsEvent, event)

        t.assertEqual(event.parser, parser)
