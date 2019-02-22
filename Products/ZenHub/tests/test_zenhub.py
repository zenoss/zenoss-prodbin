from unittest import TestCase
from mock import Mock, patch, create_autospec, call, sentinel

from zope.interface.verify import verifyObject
from zope.component import adaptedBy

from Products.ZenHub.zenhub import (
    HubWillBeCreatedEvent, IHubWillBeCreatedEvent,
    HubCreatedEvent, IHubCreatedEvent,
    ParserReadyForOptionsEvent, IParserReadyForOptionsEvent,
    ZenHub, ZCmdBase,
    ZENHUB_MODULE, QUEUEMESSAGING_MODULE,
    XML_RPC_PORT, PB_PORT,
    DefaultConfProvider, IHubConfProvider,
    DefaultHubHeartBeatCheck, IHubHeartBeatCheck,
    IEventPublisher,
    collections,
)

PATH = {'src': 'Products.ZenHub.zenhub'}


class ZenHubInitTest(TestCase):
    '''The init test is seperate from the others due to the complexity
    of the __init__ method
    '''
    @patch('{src}.InvalidationManager'.format(**PATH))
    @patch('{src}.MetricManager'.format(**PATH), autospec=True)
    @patch('{src}.HubServiceManager'.format(**PATH), autospec=True)
    @patch('{src}.load_config_override'.format(**PATH), spec=True)
    @patch('{src}.signal'.format(**PATH), spec=True)
    @patch('{src}.App_Start'.format(**PATH), spec=True)
    @patch('{src}.HubCreatedEvent'.format(**PATH), spec=True)
    @patch('{src}.zenPath'.format(**PATH), spec=True)
    @patch('{src}.reactor'.format(**PATH), spec=True)
    @patch('{src}.ContinuousProfiler'.format(**PATH), spec=True)
    @patch('{src}.HubWillBeCreatedEvent'.format(**PATH), spec=True)
    @patch('{src}.notify'.format(**PATH), spec=True)
    @patch('{src}.load_config'.format(**PATH), spec=True)
    @patch('__builtin__.super'.format(**PATH), autospec=True)
    def test___init__(
        t,
        super,
        load_config,
        notify,
        HubWillBeCreatedEvent,
        ContinuousProfiler,
        reactor,
        zenPath,
        HubCreatedEvent,
        App_Start,
        signal,
        load_config_override,
        HubServiceManager,
        MetricManager,
        InvalidationManager,
    ):
        # Mock out attributes set by the parent class
        # Because these changes are made on the class, they must be reversable
        t.zenhub_patchers = [
            patch.object(ZenHub, 'dmd', create=True),
            patch.object(ZenHub, 'log', create=True),
            patch.object(ZenHub, 'options', create=True),
            patch.object(ZenHub, 'getRRDStats', autospec=True),
            patch.object(ZenHub, '_getConf', autospec=True),
            patch.object(ZenHub, 'sendEvent', autospec=True),
            patch.object(ZenHub, 'storage', create=True),
        ]

        for patcher in t.zenhub_patchers:
            patcher.start()
            t.addCleanup(patcher.stop)

        ZenHub._getConf.return_value.id = 'config_id'
        ZenHub.storage.mock_add_spec(['poll_invalidations'])

        zh = ZenHub()

        t.assertIsInstance(zh, ZenHub)
        # Skip Metrology validation for now due to complexity
        super.return_value.__init__assert_called_with(ZenHub, zh)
        load_config.assert_called_with("hub.zcml", ZENHUB_MODULE)
        HubWillBeCreatedEvent.assert_called_with(zh)
        notify.assert_has_calls([call(HubWillBeCreatedEvent.return_value)])
        # Performance Profiling
        ContinuousProfiler.assert_called_with('zenhub', log=zh.log)
        zh.profiler.start.assert_called_with()

        # 'counters' is a ZenHub API.
        t.assertIsInstance(zh.counters, collections.Counter)

        t.assertIsInstance(zh.shutdown, bool)
        t.assertFalse(zh.shutdown)

        expected_services = HubServiceManager.return_value.services
        t.assertEqual(expected_services, zh.services)

        # Event Handler shortcut
        t.assertEqual(zh.zem, zh.dmd.ZenEventManager)

        # Messageing config, including work and invalidations
        # Patched internal import of Products.ZenMessaging.queuemessaging
        load_config_override.assert_called_with(
            'twistedpublisher.zcml',
            QUEUEMESSAGING_MODULE
        )
        HubCreatedEvent.assert_called_with(zh)
        notify.assert_called_with(HubCreatedEvent.return_value)
        zh.sendEvent.assert_called_with(
            zh, eventClass=App_Start, summary='zenhub started',
            severity=0
        )

        HubServiceManager.assert_called_once_with(
            modeling_pause_timeout=zh.options.modeling_pause_timeout,
            passwordfile=zh.options.passwordfile,
            pbport=zh.options.pbport,
            xmlrpcport=zh.options.xmlrpcport,
        )

        MetricManager.assert_called_with(
            daemon_tags={
                'zenoss_daemon': 'zenhub',
                'zenoss_monitor': zh.options.monitor,
                'internal': True
            }
        )
        t.assertEqual(zh._metric_manager, MetricManager.return_value)
        t.assertEqual(
            zh._invalidation_manager, InvalidationManager.return_value
        )

        signal.signal.assert_called_with(signal.SIGUSR2, zh.sighandler_USR2)

    def test_PbRegistration(t):
        from twisted.spread.jelly import unjellyableRegistry
        t.assertTrue('DataMaps.ObjectMap' in unjellyableRegistry)
        t.assertTrue(
            'Products.DataCollector.plugins.DataMaps.ObjectMap'
            in unjellyableRegistry
        )


class ZenHubTest(TestCase):

    def setUp(t):
        # Patch out the ZenHub __init__ method, due to excessive side-effects
        t.init_patcher = patch.object(
            ZCmdBase, '__init__', autospec=True, return_value=None
        )
        t.init_patcher.start()
        t.addCleanup(t.init_patcher.stop)

        # Mock out attributes set by ZCmdBase
        t.zcmdbase_patchers = [
            patch.object(ZenHub, 'dmd', create=True),
            patch.object(ZenHub, 'log', create=True),
            patch.object(ZenHub, 'options', create=True),
            patch.object(ZenHub, 'niceDoggie', create=True),
            patch.object(
                ZenHub, 'storage', create=True,
                set_spec=['poll_invalidations']
            ),
        ]
        for patcher in t.zcmdbase_patchers:
            patcher.start()
            t.addCleanup(patcher.stop)

        # Patch external dependencies
        needs_patching = [
            "reactor",
            "HubServiceManager",
            "InvalidationManager",
            "MetricManager",
            "notify",
            "ContinuousProfiler",
            "load_config_override",
            "load_config",
            "IHubConfProvider",
        ]
        t.patchers = {}
        for target in needs_patching:
            patched = patch(
                "{src}.{target}".format(target=target, **PATH), autospec=True
            )
            t.patchers[target] = patched
            setattr(t, target, patched.start())
            t.addCleanup(patched.stop)

        t.zh = ZenHub()

    @patch('{src}.task.LoopingCall'.format(**PATH), autospec=True)
    @patch('{src}.getUtility'.format(**PATH), autospec=True)
    def test_main(t, getUtility, LoopingCall):
        '''Daemon Entry Point
        Execution waits at reactor.run() until the reactor stops
        '''
        t.zh.options = sentinel.options
        t.zh.options.monitor = 'localhost'
        t.zh.options.cycle = True
        t.zh.options.profiling = True
        t.zh.options.invalidation_poll_interval = sentinel.inval_poll
        # Metric Management
        t.zh._metric_manager = t.MetricManager.return_value
        t.zh._metric_writer = sentinel.metric_writer
        t.zh.profiler = Mock(name='profiler', spec_set=['stop'])

        t.zh.main()

        # convert to a looping call
        t.reactor.callLater.assert_called_with(0, t.zh.heartbeat)

        t.zh._service_manager.start.assert_called_once_with(
            t.zh.dmd, t.reactor
        )

        LoopingCall.assert_called_once_with(
            t.zh._invalidation_manager.process_invalidations
        )
        t.assertEqual(
            LoopingCall.return_value, t.zh.process_invalidations_task
        )

        t.assertEqual(t.zh.metricreporter, t.zh._metric_manager.metricreporter)
        t.zh._metric_manager.start.assert_called_with()
        # trigger to shut down metric reporter before zenhub exits
        t.reactor.addSystemEventTrigger.assert_called_with(
            'before', 'shutdown', t.zh._metric_manager.stop
        )
        # After the reactor stops:
        t.zh.profiler.stop.assert_called_with()
        # Closes IEventPublisher, which breaks old integration tests
        getUtility.assert_called_with(IEventPublisher)
        getUtility.return_value.close.assert_called_with()

    @patch('{src}.reactor'.format(**PATH))
    def test_sighandler_USR2(t, reactor):
        '''Daemon function
        when signal USR2 is recieved, broadcast it to all worker processes
        '''
        ZenHub.sighandler_USR2(t.zh, signum='unused', frame='unused')
        reactor.callLater.assert_called_once_with(0, t.zh._ZenHub__dumpStats)

    def test___dumpStats(t):
        ZenHub._ZenHub__dumpStats(t.zh)

        t.zh._service_manager.getStatusReport.assert_called_once_with()
        t.zh.log.info.assert_called_once_with(
            "\n%s\n",
            t.zh._service_manager.getStatusReport.return_value
        )
        t.zh._service_manager.reportWorkerStatus.assert_called_once_with()

    @patch('{src}.super'.format(**PATH))
    @patch('{src}.signal'.format(**PATH), autospec=True)
    def test_sighandler_USR1(t, signal, super):
        '''Daemon function
        when signal USR1 is recieved, broadcast it to all worker processes
        '''
        t.zh.profiler = Mock(name='profiler', spec_set=['dump_stats'])
        t.zh.options = Mock(name='options', profiling=True)
        signum = sentinel.signum
        frame = sentinel.frame

        ZenHub.sighandler_USR1(t.zh, signum=signum, frame=frame)

        t.zh.profiler.dump_stats.assert_called_with()
        super.assert_called_with(ZenHub, t.zh)
        super.return_value.sighandler_USR1.assert_called_with(
            signum, frame
        )

    def test_stop(t):
        t.assertFalse(t.zh.shutdown)
        t.zh.stop()
        t.assertTrue(t.zh.shutdown)

    def test__getConf(t):
        ret = t.zh._getConf()
        confProvider = t.IHubConfProvider.return_value
        t.assertEqual(ret, confProvider.getHubConf.return_value)

    def test_getService(t):
        service = "service"
        monitor = "localhost"
        services = t.zh._service_manager.services
        expected = services.getService.return_value

        result = t.zh.getService(service, monitor)

        t.assertEqual(expected, result)
        services.getService.assert_called_once_with(service, monitor)

    def test_getRRDStats(t):
        t.zh._metric_manager = t.MetricManager.return_value
        t.zh._getConf = create_autospec(t.zh._getConf)

        ret = t.zh.getRRDStats()

        t.zh._metric_manager.get_rrd_stats.assert_called_with(
            t.zh._getConf(), t.zh.zem.sendEvent
        )
        t.assertEqual(ret, t.zh._metric_manager.get_rrd_stats.return_value)

    def test_processQueue(t):
        t.zh.processQueue()
        t.zh._invalidation_manager.process_invalidations.assert_called_with()

    def test__initialize_invalidation_filters(t):
        t.zh._initialize_invalidation_filters()
        t.zh._invalidation_manager\
            .initialize_invalidation_filters.assert_called_with()

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

    @patch('{src}.IHubHeartBeatCheck'.format(**PATH), autospec=True)
    @patch('{src}.EventHeartbeat'.format(**PATH), autospec=True)
    def test_heartbeat(t, EventHeartbeat, IHubHeartBeatCheck):
        '''Event Management / Daemon Function
        Also, some Metrics Reporting stuff for fun
        '''
        t.zh.options = Mock(
            name='options', spec_set=['monitor', 'name', 'heartbeatTimeout'],
        )
        t.zh._invalidation_manager.totalTime = 100
        t.zh._invalidation_manager.totalEvents = 20
        # static value defined in function
        seconds = 30
        # Metrics reporting portion needs to be factored out
        service0 = Mock(name='service0', spec_set=['callTime'], callTime=9)
        t.zh._service_manager.services = {'service0': service0}
        t.zh._service_manager.worklist = [sentinel.work0, sentinel.work1]

        t.zh.heartbeat()

        EventHeartbeat.assert_called_with(
            t.zh.options.monitor, t.zh.name, t.zh.options.heartbeatTimeout
        )
        t.zh.zem.sendEvent.assert_called_with(EventHeartbeat.return_value)
        t.zh.niceDoggie.assert_called_with(seconds)
        t.reactor.callLater.assert_called_with(seconds, t.zh.heartbeat)
        IHubHeartBeatCheck.assert_called_with(t.zh)
        IHubHeartBeatCheck.return_value.check.assert_called_with()
        # Metrics reporting, copies zenhub.counters into rrdStats.counter
        t.zh.rrdStats.counter.has_calls([
            call('totalTime', int(t.zh.totalTime * 1000)),
            call('totalEvents', t.zh.totalEvents),
            call('totalCallTime', sum(
                s.callTime for s in t.zh._service_manager.services.values()
            )),
        ])
        t.zh.rrdStats.gauge.assert_has_calls([
            call('services', len(t.zh._service_manager.services)),
            call('workListLength', len(t.zh._service_manager.worklist)),
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
        t.assertEqual(t.zh.options.workersReservedForEvents, 1)
        t.assertEqual(t.zh.options.invalidation_poll_interval, 30)
        t.assertEqual(t.zh.options.profiling, False)
        t.assertEqual(t.zh.options.modeling_pause_timeout, 3600)
        # delay before actually parsing the options
        notify.assert_called_with(ParserReadyForOptionsEvent(t.zh.parser))


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
