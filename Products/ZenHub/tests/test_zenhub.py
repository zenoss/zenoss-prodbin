from unittest import TestCase
from mock import Mock, patch, create_autospec, call

from zope.interface.verify import verifyObject

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
    metricWriter,
    ZenHub,
    CONNECT_TIMEOUT, OPTION_STATE,
)

PATH = {'src': 'Products.ZenHub.zenhub'}


class AuthXmlRpcServiceTest(TestCase):

    def setUp(t):
        t.dmd = Mock(name='dmd', spec_set=['ZenEventManager'])
        t.checker = Mock(name='checker', spec_set=['requestAvatarId'])

        t.axrs = AuthXmlRpcService(t.dmd, t.checker)

    @patch('{src}.XmlRpcService.__init__'.format(**PATH), autospec=True)
    def test___init__(t, XmlRpcService__init__):
        dmd = Mock(name='dmd', spec_set=[])
        checker = Mock(name='checker', spec_set=[])

        axrs = AuthXmlRpcService(dmd, checker)

        XmlRpcService__init__.assert_called_with(axrs, dmd)
        t.assertEqual(axrs.checker, checker)

    def test_doRender(t):
        '''should be refactored to call self.render,
        instead of the parrent class directly
        '''
        render = create_autospec(XmlRpcService.render, name='render')
        XmlRpcService.render = render
        request = Mock(name='request', spec_set=[])

        ret = t.axrs.doRender('unused arg', request)

        XmlRpcService.render.assert_called_with(t.axrs, request)
        t.assertEqual(ret, render.return_value)

    @patch('{src}.xmlrpc'.format(**PATH), name='xmlrpc', autospec=True)
    def test_unauthorized(t, xmlrpc):
        request = Mock(name='request', spec_set=[])
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


class HubAvitarTest(TestCase):

    def setUp(t):
        t.hub = Mock(name='hub', spec_set=['getService', 'log', 'workers'])
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
        listener = Mock(name='listener', spec_set=[])
        options = Mock(name='options', spec_set=[])
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
        pid = 9999
        t.hub.workers = []

        t.avitar.perspective_reportingForWork(worker, pid=pid)

        t.assertFalse(worker.busy)
        t.assertEqual(worker.pid, pid)
        t.assertIn(worker, t.hub.workers)

        # Ugly test for the notifyOnDisconnect method, please refactor
        args, kwargs = worker.notifyOnDisconnect.call_args
        removeWorker = args[0]

        removeWorker(worker)
        t.assertNotIn(worker, t.hub.workers)


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
        hub = Mock(name='zenhub_instance', spec_set=[])
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
        hub = Mock(name='zenhub_instance', spec_set=[])
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
        parser = Mock(name='parser', spec_set=[])
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
        wl = _ZenHubWorklist()
        t.assertEqual(wl['sendEvents'], t.wl.eventworklist)
        t.assertEqual(wl['sendEvent'], t.wl.eventworklist)
        t.assertEqual(wl['applyDataMaps'], t.wl.applyworklist)
        t.assertEqual(wl['anything else'], t.wl.otherworklist)

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

    @patch('{src}.AggregateMetricWriter'.format(**PATH), autospec=True)
    @patch('{src}.FilteredMetricWriter'.format(**PATH), autospec=True)
    @patch('{src}.publisher'.format(**PATH), autospec=True)
    @patch('{src}.os'.format(**PATH), autospec=True)
    @patch('{src}.redisPublisher'.format(**PATH), autospec=True)
    @patch('{src}.MetricWriter'.format(**PATH), autospec=True)
    def test_metricWriter(
        t,
        MetricWriter,
        redisPublisher,
        os,
        publisher,
        FilteredMetricWriter,
        AggregateMetricWriter
    ):
        '''Returns an initialized MetricWriter instance,
        should probably be refactored into its own class
        '''
        os.environ = {
            'CONTROLPLANE': '1',
            'CONTROLPLANE_CONSUMER_URL': 'consumer_url',
            'CONTROLPLANE_CONSUMER_USERNAME': 'consumer_username',
            'CONTROLPLANE_CONSUMER_PASSWORD': 'consumer_password',
        }

        ret = metricWriter()

        MetricWriter.assert_called_with(redisPublisher.return_value)
        publisher.assert_called_with(
            os.environ['CONTROLPLANE_CONSUMER_USERNAME'],
            os.environ['CONTROLPLANE_CONSUMER_PASSWORD'],
            os.environ['CONTROLPLANE_CONSUMER_URL'],
        )
        AggregateMetricWriter.assert_called_with(
            [MetricWriter.return_value, FilteredMetricWriter.return_value]
        )
        t.assertEqual(ret, AggregateMetricWriter.return_value)


class ZenHubInitTest(TestCase):
    '''The init test is seperate from the others due to the complexity
    of the __init__ method
    '''

    @patch('{src}.signal'.format(**PATH), spec=True)
    @patch('{src}.App_Start'.format(**PATH), spec=True)
    @patch('{src}.HubCreatedEvent'.format(**PATH), spec=True)
    @patch('{src}.pb'.format(**PATH), spec=True)
    @patch('{src}.zenPath'.format(**PATH), spec=True)
    @patch('{src}.server'.format(**PATH), spec=True)
    @patch('{src}.AuthXmlRpcService'.format(**PATH), spec=True)
    @patch('{src}.reactor'.format(**PATH), spec=True)
    @patch('{src}.ipv6_available'.format(**PATH), spec=True)
    @patch('{src}.portal'.format(**PATH), spec=True)
    @patch('{src}.HubRealm'.format(**PATH), spec=True)
    @patch('{src}.loadPlugins'.format(**PATH), spec=True)
    @patch('{src}.WorkerSelector'.format(**PATH), spec=True)
    @patch('{src}.ContinuousProfiler'.format(**PATH), spec=True)
    @patch('{src}.HubWillBeCreatedEvent'.format(**PATH), spec=True)
    @patch('{src}.notify'.format(**PATH), spec=True)
    @patch('{src}.load_config'.format(**PATH), spec=True)
    @patch('{src}._ZenHubWorklist'.format(**PATH), spec=True)
    @patch('{src}.ZCmdBase.__init__'.format(**PATH), spec=True)
    def test___init__(
        t,
        CmdBase___init__,
        _ZenHubWorklist,
        load_config,
        notify,
        HubWillBeCreatedEvent,
        ContinuousProfiler,
        WorkerSelector,
        loadPlugins,
        HubRealm,
        portal,
        ipv6_available,
        reactor,
        AuthXmlRpcService,
        server,
        zenPath,
        pb,
        HubCreatedEvent,
        App_Start,
        signal,
    ):

        # Mock out attributes set the parent class
        # Because these changes are made on the class, they must be reversable
        zenhub_patchers = [
            patch.object(ZenHub, 'dmd', create=True),
            patch.object(ZenHub, 'log', create=True),
            patch.object(ZenHub, 'options', create=True),
            patch.object(ZenHub, 'loadChecker', autospec=True),
            patch.object(ZenHub, 'getRRDStats', autospec=True),
            patch.object(ZenHub, '_getConf', autospec=True),
            patch.object(ZenHub, '_createWorkerConf', autospec=True),
            patch.object(ZenHub, 'createWorker', autospec=True),
            patch.object(ZenHub, 'setKeepAlive', autospec=True),
            patch.object(ZenHub, 'sendEvent', autospec=True),
        ]

        for patcher in zenhub_patchers:
            patcher.start()

        ZenHub.options.workers = 10
        ZenHub._getConf.return_value.id = 'config_id'
        ipv6_available.return_value = False

        zh = ZenHub()
        t.assertIsInstance(zh, ZenHub)

        t.assertEqual(zh.workList, _ZenHubWorklist.return_value)
        # Skip Metrology validation for now due to complexity
        HubWillBeCreatedEvent.assert_called_with(zh)
        notify.assert_has_calls([call(HubWillBeCreatedEvent.return_value)])
        # Performance Profiling
        ContinuousProfiler.assert_called_with('zenhub', log=zh.log)
        zh.profiler.start.assert_called_with()
        # Worklist, used to delegate jobs to workers
        # TODO: move worker management into its own manager class
        WorkerSelector.assert_called_with(zh.options)
        t.assertEqual(zh.workerselector, WorkerSelector.return_value)
        # check this, was it supposed to be set on workerselector?
        t.assertEqual(zh.workList.log, zh.log)
        t.assertLess(zh.options.workersReservedForEvents, zh.options.workers)
        # Event Handler shortcut
        t.assertEqual(zh.zem, zh.dmd.ZenEventManager)
        loadPlugins.assert_called_with(zh.dmd)
        # PB, and XMLRPC communication config.
        # TODO: move this into its own manager class
        HubRealm.assert_called_with(zh)
        zh.setKeepAlive.assert_called_with(
            zh, reactor.listenTCP.return_value.socket
        )

        pb.PBServerFactory.assert_called_with(portal.Portal.return_value)
        AuthXmlRpcService.assert_called_with(
            zh.dmd, zh.loadChecker.return_value
        )
        server.Site.assert_called_with(AuthXmlRpcService.return_value)
        reactor.listenTCP.assert_has_calls([
            call(
                zh.options.pbport,
                pb.PBServerFactory.return_value,
                interface=''
            ),
            call(
                zh.options.xmlrpcport,
                server.Site.return_value,
                interface=''
            )
        ])
        # Messageing config, including work and invalidations
        # skip for now due to internal import
        #load_config_override.assert_called_with(
        #    'twistedpublisher.zcml',
        #    Products.ZenMessaging.queuemessaging
        #)
        HubCreatedEvent.assert_called_with(zh)
        notify.assert_called_with(HubCreatedEvent.return_value)
        zh.sendEvent.assert_called_with(
            zh, eventClass=App_Start, summary='zenhub started',
            severity=0
        )

        # Additional worker management, separated from the rest
        zenPath.assert_called_with('var', 'zenhub', 'config_id_worker.conf')
        t.assertEqual(zh.workerconfig, zenPath.return_value)
        zh._createWorkerConf.assert_called_with(zh)
        zh.createWorker.assert_has_calls(
            [call(zh, i) for i in range(zh.options.workers)]
        )
        # Convert this to a LoopingCall
        reactor.callLater.assert_called_with(2, zh.giveWorkToWorkers, True)
        signal.signal.assert_called_with(signal.SIGUSR2, zh.sighandler_USR2)

        for patcher in zenhub_patchers:
            patcher.stop()


class ZenHubTest(TestCase):

    def setUp(t):
        # Patch out the ZenHub __init__ method, due to excessive side-effects
        t.init_patcher = patch.object(
            ZenHub, '__init__', autospec=True, return_value=None
        )
        t.init_patcher.start()

        t.zh = ZenHub()
        # Set attributes that should be created by __init__
        t.zh.log = Mock(name='log', spec_set=['debug'])
        t.zh.shutdown = False

    def tearDown(t):
        t.init_patcher.stop()

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
        t.zh.setKeepAlive(sock)
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

    @patch('{src}.signal'.format(**PATH), autospec=True)
    @patch('{src}.time'.format(**PATH), autospec=True)
    def test_sighandler_USR2(t, time, signal):
        '''when signal USR2 is recieved, broadcast it to all worker processes
        '''
        zh = Mock(ZenHub, name='ZenHub')
        zh.log = Mock(name='log')
        zh.SIGUSR_TIMEOUT = 1
        # should use the workerProcess class as spec, but its currently burried
        worker_proc = Mock(
            name='worker_1', spec_set=['spawn_time', 'signalProcess'],
            spawn_time=3
        )
        time.time.return_value = 5
        zh.workerprocessmap = {'w1': worker_proc}

        ZenHub.sighandler_USR2(zh, signum='unused', frame='unused')

        worker_proc.signalProcess.assert_called_with(signal.SIGUSR2)

    @patch('{src}.super'.format(**PATH))
    @patch('{src}.signal'.format(**PATH), autospec=True)
    @patch('{src}.time'.format(**PATH), autospec=True)
    def test_sighandler_USR1(t, time, signal, super):
        '''when signal USR1 is recieved, broadcast it to all worker processes
        '''
        zh = Mock(ZenHub, name='ZenHub')
        zh.profiler = Mock(name='profiler', spec_set=['dump_stats'])
        zh.options = Mock(name='options', profiling=True)
        worker_proc = Mock(name='worker_1', spec_set=['signalProcess'])
        zh.workerprocessmap = {'w1': worker_proc}
        signum = Mock(name='signum', spec_set=[])
        frame = Mock(name='frame', spec_set=[])

        ZenHub.sighandler_USR1(zh, signum=signum, frame=frame)

        zh.profiler.dump_stats.assert_called_with()
        super.assert_called_with(ZenHub, zh)
        super.return_value.sighandler_USR1.assert_called_with(
            signum, frame
        )
        worker_proc.signalProcess.assert_called_with(signal.SIGUSR1)

    def test_stop(t):
        t.assertFalse(t.zh.shutdown)
        t.zh.stop()
        t.assertTrue(t.zh.shutdown)

    @patch('{src}.IHubConfProvider'.format(**PATH), autospec=True)
    def test__getConf(t, IHubConfProvider):
        ret = t.zh._getConf()
        confProvider = IHubConfProvider.return_value
        t.assertEqual(ret, confProvider.getHubConf.return_value)
