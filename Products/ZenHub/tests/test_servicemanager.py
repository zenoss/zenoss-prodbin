##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import time

from unittest import TestCase, skip
from mock import Mock, patch, create_autospec, call, MagicMock, sentinel

from zope.interface.verify import verifyObject

from Products.ZenHub.dispatchers.workers import JobStats, WorkerStats
from Products.ZenHub.servicemanager import (
    AuthXmlRpcService,
    DispatchingExecutor,
    getCredentialCheckers,
    HubAvatar,
    HubRealm,
    HubServiceManager,
    WorkerInterceptor,
    WorkerInterceptorFactory,
    HubServiceRegistry,
    RemoteBadMonitor, UnknownServiceError, RemoteException,
    ServiceAddedEvent, IServiceAddedEvent,
    ZenHubPriority,
    pb, defer,
)

PATH = {'src': 'Products.ZenHub.servicemanager'}


class Callback(object):
    """Helper class for capturing the results of Twisted Deferred objects.

    Callback objects can be used for both successful and errored results.

    The result is stored in the 'result' attribute of the Callback object.

    E.g.
        cb = Callback()
        dfr = obj.returns_a_deferred()
        dfr.addCallback(cb)

        self.assertTrue(cb.result)
    """

    def __init__(self):
        """Initialize a Callback instance."""
        self.result = None

    def __call__(self, r):
        """Save the result."""
        self.result = r


class HubServiceManagerTest(TestCase):
    """Test the HubServiceManager class."""

    def setUp(self):
        self.modeling_pause_timeout = 1.0
        self.passwordfile = "file"
        self.pbport = 5000
        self.xmlrpcport = 6000

    def test_init(self):
        # No exception should be raised.
        HubServiceManager(
            modeling_pause_timeout=self.modeling_pause_timeout,
            passwordfile=self.passwordfile,
            pbport=self.pbport,
            xmlrpcport=self.xmlrpcport,
        )

    def test_init_missing_modeling_pause_timeout(self):
        with self.assertRaisesRegexp(TypeError, ".*modeling_pause_timeout.*"):
            HubServiceManager(
                passwordfile=self.passwordfile,
                pbport=self.pbport,
                xmlrpcport=self.xmlrpcport,
            )

    def test_init_missing_passwordfile(self):
        with self.assertRaisesRegexp(TypeError, ".*passwordfile.*"):
            HubServiceManager(
                modeling_pause_timeout=self.modeling_pause_timeout,
                pbport=self.pbport,
                xmlrpcport=self.xmlrpcport,
            )

    def test_init_missing_pbport(self):
        with self.assertRaisesRegexp(TypeError, ".*pbport.*"):
            HubServiceManager(
                modeling_pause_timeout=self.modeling_pause_timeout,
                passwordfile=self.passwordfile,
                xmlrpcport=self.xmlrpcport,
            )

    def test_init_missing_xmlrpcport(self):
        with self.assertRaisesRegexp(TypeError, ".*xmlrpcport.*"):
            HubServiceManager(
                modeling_pause_timeout=self.modeling_pause_timeout,
                passwordfile=self.passwordfile,
                pbport=self.pbport,
            )

    @patch("{src}.ModelingPaused".format(**PATH), autospec=True)
    @patch("{src}.ZenHubWorklist".format(**PATH), autospec=True)
    @patch("{src}.register_metrics_on_worklist".format(**PATH), autospec=True)
    @patch("{src}.WorkerPoolDispatcher".format(**PATH), autospec=True)
    @patch("{src}.WorkerPool".format(**PATH), autospec=True)
    @patch("{src}.StatsMonitor".format(**PATH), autospec=True)
    @patch("{src}.EventDispatcher".format(**PATH), autospec=True)
    @patch("{src}.DispatchingExecutor".format(**PATH), autospec=True)
    @patch("{src}.WorkerInterceptorFactory".format(**PATH), autospec=True)
    @patch("{src}.HubServiceRegistry".format(**PATH), autospec=True)
    @patch("{src}.HubAvatar".format(**PATH), autospec=True)
    @patch("{src}.HubRealm".format(**PATH), autospec=True)
    @patch("{src}.getCredentialCheckers".format(**PATH), autospec=True)
    @patch("{src}.portal.Portal".format(**PATH), autospec=True)
    @patch("{src}.ZenPBServerFactory".format(**PATH), autospec=True)
    @patch("{src}.ipv6_available".format(**PATH), autospec=True)
    @patch("{src}.serverFromString".format(**PATH), autospec=True)
    @patch("{src}.AuthXmlRpcService".format(**PATH))
    def test_start(
        self,
        authXmlRpcService,
        serverFromString,
        ipv6_available,
        pbServerFactory,
        portal,
        getCredentialCheckers,
        hubRealm,
        hubAvatar,
        hubServiceRegistry,
        hubServiceReferenceFactory,
        dispatchingExecutor,
        eventDispatcher,
        statsMonitor,
        workerPool,
        workerPoolDispatcher,
        register_metrics_on_worklist,
        zenHubWorklist,
        modelingPaused,
    ):
        dmd = Mock("dmd", spec_set=["ZenEventManager"])
        reactor = Mock()

        paused = modelingPaused.return_value
        worklist = zenHubWorklist.return_value
        workers = workerPoolDispatcher.return_value
        stats = statsMonitor.return_value
        pool = workerPool.return_value
        events = eventDispatcher.return_value
        executor = dispatchingExecutor.return_value
        service_factory = hubServiceReferenceFactory.return_value
        services = hubServiceRegistry.return_value
        avatar = hubAvatar.return_value
        realm = hubRealm.return_value
        checker = Mock()
        checkers = [checker]
        getCredentialCheckers.return_value = checkers
        portalObj = portal.return_value
        pb_factory = pbServerFactory.return_value
        xmlrpc_site = authXmlRpcService.makeSite.return_value

        ipv6_available.side_effect = lambda: True
        tcp_version = "tcp6"
        pb_descriptor = "%s:port=%s" % (tcp_version, self.pbport)
        xmlrpc_descriptor = "%s:port=%s" % (tcp_version, self.xmlrpcport)

        pb_server = Mock()
        dfr = pb_server.listen.return_value

        xmlrpc_server = Mock()

        def serverFromStringSideEffect(r, d):
            if d == pb_descriptor:
                return pb_server
            return xmlrpc_server

        serverFromString.side_effect = serverFromStringSideEffect

        manager = HubServiceManager(
            modeling_pause_timeout=self.modeling_pause_timeout,
            passwordfile=self.passwordfile,
            pbport=self.pbport,
            xmlrpcport=self.xmlrpcport,
        )
        manager.start(dmd, reactor)

        modelingPaused.assert_called_once_with(
            dmd, self.modeling_pause_timeout,
        )
        zenHubWorklist.assert_called_once_with(modeling_paused=paused)
        register_metrics_on_worklist.assert_called_once_with(worklist)
        workerPoolDispatcher.assert_called_once_with(
            reactor, worklist, pool, stats,
        )
        eventDispatcher.assert_called_once_with(dmd.ZenEventManager)
        dispatchingExecutor.assert_called_once_with([events], default=workers)
        hubServiceReferenceFactory.assert_called_once_with(executor)
        hubServiceRegistry.assert_called_once_with(dmd, service_factory)
        hubAvatar.assert_called_once_with(services, pool)
        hubRealm.assert_called_once_with(avatar)
        getCredentialCheckers.assert_called_once_with(self.passwordfile)
        portal.assert_called_once_with(realm, checkers)
        pbServerFactory.assert_called_once_with(portalObj)

        serverFromString.assert_has_calls([
            call(reactor, pb_descriptor),
            call(reactor, xmlrpc_descriptor),
        ])

        pb_server.listen.assert_called_once_with(pb_factory)
        dfr.addCallback.assert_called_once_with(
            manager._HubServiceManager__setKeepAlive,
        )
        authXmlRpcService.makeSite.assert_called_once_with(dmd, checker)
        xmlrpc_server.listen.assert_called_once_with(xmlrpc_site)

    @skip("Not testing string formatting")
    @patch("{src}.StatsMonitor".format(**PATH), autospec=True)
    @patch("{src}.get_worklist_metrics".format(**PATH), autospec=True)
    def test_getStatusReport(self, getWorklistMetrics, statsMonitor):
        gauges = {
            ZenHubPriority.EVENTS: 3404,
            ZenHubPriority.OTHER: 276,
            ZenHubPriority.MODELING: 169,
            ZenHubPriority.SINGLE_MODELING: 23,
        }
        now = time.time() - (1350)
        workTracker = {
            0: WorkerStats(
                "Busy", "localhost:EventServer:sendEvent", now, 34.8,
            ),
            1: WorkerStats(
                "Idle", "localhost:SomeService:someMethod", now, 4054.3,
            ),
            2: None,
        }
        execTimer = {
            "sendEvent": Mock(
                JobStats,
                count=2953, idle_total=3422.3, running_total=35.12,
                last_called_time=now,
            ),
            "sendEvents": Mock(
                JobStats,
                count=451, idle_total=3632.5, running_total=20.5,
                last_called_time=now,
            ),
            "applyDataMaps": Mock(
                JobStats,
                count=169, idle_total=620.83, running_total=3297.248,
                last_called_time=now,
            ),
            "singleApplyDataMaps": Mock(
                JobStats,
                count=23, idle_total=1237.345, running_total=936.85,
                last_called_time=now,
            ),
            "someMethod": Mock(
                JobStats,
                count=276, idle_total=7384.3, running_total=83.3,
                last_called_time=now,
            ),
        }
        getWorklistMetrics.return_value = gauges
        stats = statsMonitor.return_value
        stats.workers = workTracker
        stats.jobs = execTimer
        manager = HubServiceManager(
            modeling_pause_timeout=self.modeling_pause_timeout,
            passwordfile=self.passwordfile,
            pbport=self.pbport,
            xmlrpcport=self.xmlrpcport,
        )
        print manager.getStatusReport()


class HubRealmTest(TestCase):
    """Test the HubRealm class."""

    def setUp(self):
        self.avatar = Mock(HubAvatar)
        self.realm = HubRealm(self.avatar)

    def test_requestAvatar(self):
        cid = "admin"
        mind = object()
        intfs = [pb.IPerspective]

        actual = self.realm.requestAvatar(cid, mind, *intfs)
        self.assertTrue(len(actual), 3)

        intf, avatar, callback = actual
        self.assertEqual(intf, pb.IPerspective)
        self.assertEqual(avatar, self.avatar)
        self.assertTrue(callable(callback))


class MockWorker(object):
    """Mock zenhubworker reference.

    Used to implement the notifyOnDisconnect event handler.
    """

    def __init__(self):
        """Initialize a MockWorker instance."""
        self.__cb = None

    def notifyOnDisconnect(self, cb):
        self.__cb = cb

    def disconnect(self):
        self.__cb(self)


class HubAvatarTest(TestCase):
    """Test the HubAvatar class."""

    def setUp(self):
        self.getLogger_patcher = patch(
            "{src}.getLogger".format(**PATH), autospec=True,
        )
        self.getLogger = self.getLogger_patcher.start()
        self.addCleanup(self.getLogger_patcher.stop)
        self.services = create_autospec(HubServiceRegistry)
        self.workers = set()  # only __contains__, add, and remove needed
        self.avatar = HubAvatar(self.services, self.workers)

    def test_perspective_ping(self):
        ret = self.avatar.perspective_ping()
        self.assertEqual(ret, 'pong')

    @patch('{src}.os.environ'.format(**PATH), name='os.environ', autospec=True)
    def test_perspective_getHubInstanceId_normal(self, os_environ):
        key = "CONTROLPLANE_INSTANCE_ID"
        hubId = "hub"

        def side_effect(k, d):
            if k == key:
                return hubId
            return d

        os_environ.get.side_effect = side_effect

        actual = self.avatar.perspective_getHubInstanceId()

        self.assertEqual(actual, hubId)

    @patch('{src}.os.environ'.format(**PATH), name='os.environ', autospec=True)
    def test_perspective_getHubInstanceId_unknown(self, os_environ):
        os_environ.get.side_effect = lambda k, d: d
        actual = self.avatar.perspective_getHubInstanceId()
        self.assertEqual(actual, "Unknown")

    def test_perspective_getService_no_listener(self):
        service_name = "testservice"
        monitor = "localhost"

        expected = self.services.getService.return_value
        actual = self.avatar.perspective_getService(service_name, monitor)

        self.services.getService.assert_called_with(service_name, monitor)
        expected.addListener.assert_not_called()
        self.assertEqual(expected, actual)

    def test_perspective_getService_with_listener(self):
        service_name = "testservice"
        monitor = "localhost"
        listener = sentinel.listener
        options = sentinel.options

        expected = self.services.getService.return_value
        actual = self.avatar.perspective_getService(
            service_name, monitor, listener=listener, options=options,
        )

        self.services.getService.assert_called_with(service_name, monitor)
        expected.addListener.assert_called_once_with(listener, options)
        self.assertEqual(expected, actual)

    def test_perspective_getService_raises_RemoteBadMonitor(self):
        self.services.getService.side_effect = RemoteBadMonitor('tb', 'msg')
        with self.assertRaises(RemoteBadMonitor):
            self.avatar.perspective_getService('service_name')

    @patch("{src}.getLogger".format(**PATH))
    def test_perspective_getService_raises_error(self, getLogger):
        logger = getLogger.return_value
        self.avatar._HubAvatar__log = logger
        service_name = "service_name"
        self.services.getService.side_effect = Exception()

        with self.assertRaises(pb.Error):
            self.avatar.perspective_getService(service_name)
            logger.exception.assert_called_once_with(
                "Failed to get service '%s'", service_name,
            )

    def test_perspective_reportingForWork(self):
        worker = MockWorker()
        workerId = "1"

        self.avatar.perspective_reportingForWork(worker, workerId)

        self.assertTrue(hasattr(worker, "busy"))
        self.assertFalse(worker.busy)

        self.assertTrue(hasattr(worker, "workerId"))
        self.assertEqual(worker.workerId, workerId)

        self.assertIn(worker, self.workers)

        worker.disconnect()
        self.assertNotIn(worker, self.workers)


class HubServiceRegistryTest(TestCase):
    """Test the HubServiceRegistry class."""

    def setUp(self):
        self.getLogger_patcher = patch(
            "{src}.getLogger".format(**PATH), autospec=True,
        )
        self.getLogger = self.getLogger_patcher.start()
        self.addCleanup(self.getLogger_patcher.stop)

        self.dmd = Mock()
        self.factory = MagicMock(WorkerInterceptorFactory)
        self.manager = HubServiceRegistry(self.dmd, self.factory)

    @patch("{src}.ServiceAddedEvent".format(**PATH), spec=True)
    @patch("{src}.notify".format(**PATH), spec=True)
    @patch("{src}.importClass".format(**PATH), autospec=True)
    def test_getService(self, importClass, notify, addedEvent):
        self.dmd.Monitors.Performance._getOb.return_value = True
        name = "service"
        monitor = "localhost"
        serviceClass = importClass.return_value
        service = serviceClass.return_value

        expected = self.factory.build.return_value

        s1 = self.manager.getService(name, monitor)
        s2 = self.manager.getService(name, monitor)

        self.factory.build.assert_called_once_with(service, name, monitor)

        self.assertEqual(expected, s1)
        self.assertEqual(expected, s2)

        serviceClass.assert_called_once_with(self.dmd, monitor)
        addedEvent.assert_called_once_with(name, monitor)
        notify.assert_called_once_with(addedEvent.return_value)

    def test_getService_bad_monitor(self):
        self.dmd.Monitors.Performance._getOb.return_value = False
        name = "service"
        monitor = "bad"

        with self.assertRaisesRegexp(RemoteBadMonitor, ".*bad.*"):
            self.manager.getService(name, monitor)

    @patch("{src}.importClass".format(**PATH), spec=True)
    def test_getService_unknown_service(self, importClass):
        self.dmd.Monitors.Performance._getOb.return_value = True
        name = "service"
        monitor = "localhost"
        importClass.side_effect = ImportError()

        with self.assertRaisesRegexp(UnknownServiceError, ".*service.*"):
            self.manager.getService(name, monitor)

        importClass.assert_has_calls([
            call(name),
            call("Products.ZenHub.services.%s" % name, name),
        ])
        self.factory.build.assert_not_called()

    @patch("{src}.importClass".format(**PATH), spec=True)
    def test_getService_bad_service(self, importClass):
        self.dmd.Monitors.Performance._getOb.return_value = True
        name = "service"
        monitor = "localhost"

        service = Mock()
        excp = ValueError()
        service.side_effect = excp

        importClass.return_value = service

        with self.assertRaises(ValueError):
            self.manager.getService(name, monitor)

        importClass.assert_called_once_with(name)
        service.assert_called_once_with(self.dmd, monitor)
        self.factory.build.assert_not_called()


class WorkerInterceptorFactoryTest(TestCase):
    """Test the WorkerInterceptorFactory class."""

    def setUp(self):
        self.dispatcher = Mock()
        self.factory = WorkerInterceptorFactory(self.dispatcher)

    @patch("{src}.WorkerInterceptor".format(**PATH), autospec=True)
    def test_build(self, ref):
        name = "service"
        monitor = "localhost"
        service = Mock()

        expected = ref.return_value
        actual = self.factory.build(service, name, monitor)

        self.assertEqual(expected, actual)
        ref.assert_called_once_with(service, name, monitor, self.dispatcher)


class WorkerInterceptorTest(TestCase):
    """Test the WorkerInterceptor class."""

    def setUp(self):
        self.getLogger_patcher = patch(
            "{src}.getLogger".format(**PATH), autospec=True,
        )
        self.getLogger = self.getLogger_patcher.start()
        self.addCleanup(self.getLogger_patcher.stop)

        self.name = "service"
        self.monitor = "monitor"
        self.service = Mock()
        self.executor = MagicMock(DispatchingExecutor)
        self.reference = WorkerInterceptor(
            self.service, self.name, self.monitor, self.executor,
        )
        self.reference.perspective = sentinel.perspective

        self.broker = Mock()
        self.broker.unserialize.side_effect = lambda d: d
        self.broker.serialize.side_effect = lambda d, p: d

    def test_service_property(self):
        self.assertEqual(self.service, self.reference.service)

    @patch("{src}.ServiceCallJob".format(**PATH), autospec=True)
    def test_remoteMessageReceived(self, serviceJob):
        args = []
        kwargs = {}
        method = "method"

        state = object()
        self.executor.submit.side_effect = lambda j: defer.succeed(state)
        job = serviceJob.return_value

        dfr = self.reference.remoteMessageReceived(
            self.broker, method, args, kwargs,
        )

        self.assertEqual(dfr.result, state)
        self.executor.submit.assert_called_once_with(job)
        serviceJob.assert_called_once_with(
            self.name, self.monitor, method, args, kwargs,
        )
        self.broker.unserialize.assert_has_calls([
            call(args), call(kwargs),
        ])
        self.broker.serialize.assert_called_once_with(
            state, self.reference.perspective,
        )

    def test_remoteMessageReceived_raise_external_error(self):
        args = []
        kwargs = {}

        exceptions = [
            pb.Error(ValueError("boom")),
            pb.RemoteError("ValueError", "boom", "[no traceback]"),
            RemoteException("boom", "tb"),
        ]
        for expected_ex in exceptions:
            self.executor.submit.side_effect = \
                lambda j: defer.fail(expected_ex)

            cb = Callback()
            dfr = self.reference.remoteMessageReceived(
                self.broker, "method", args, kwargs,
            )
            dfr.addErrback(cb)

            try:
                self.broker.unserialize.assert_has_calls([
                    call(args), call(kwargs),
                ])
                self.broker.serialize.assert_not_called()
                self.assertEqual(cb.result.value, expected_ex)
            except Exception as ex:
                ex.args = (ex.args[0] + " [exception=%r]" % (expected_ex,),)
                raise

    def test_remoteMessageReceived_raise_exception(self):
        args = []
        kwargs = {}
        ex = ValueError("boom")
        self.executor.submit.side_effect = lambda j: defer.fail(ex)

        dfr = self.reference.remoteMessageReceived(
            self.broker, "method", args, kwargs,
        )
        dfr.addErrback(lambda f: (f.trap(pb.Error), f))
        exType, failure = dfr.result

        self.broker.unserialize.assert_has_calls([
            call(args), call(kwargs),
        ])
        self.broker.serialize.assert_not_called()
        self.assertIs(exType, pb.Error)
        self.assertIn(repr(ex), failure.value.args[0])


class ServiceAddedEventTest(TestCase):
    """Test the ServiceAddedEvent class."""

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


class AuthXmlRpcServiceTest(TestCase):
    """Test the AuthXmlRpcService class."""

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

    @patch("{src}.XmlRpcService.render".format(**PATH), autospec=True)
    def test_doRender(t, render):
        request = sentinel.request

        result = t.axrs.doRender('unused arg', request)

        render.assert_called_with(t.axrs, request)
        t.assertEqual(result, render.return_value)

    @patch('{src}.xmlrpc'.format(**PATH), name='xmlrpc', autospec=True)
    def test_unauthorized(t, xmlrpc):
        request = sentinel.request
        t.axrs._cbRender = create_autospec(t.axrs._cbRender)

        t.axrs.unauthorized(request)

        xmlrpc.Fault.assert_called_with(t.axrs.FAILURE, 'Unauthorized')
        t.axrs._cbRender.assert_called_with(xmlrpc.Fault.return_value, request)

    @patch('{src}.server'.format(**PATH), name='server', autospec=True)
    @patch(
        '{src}.credentials'.format(**PATH), name='credentials', autospec=True,
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
            credentials.UsernamePassword.return_value,
        )
        deferred = t.axrs.checker.requestAvatarId.return_value
        deferred.addCallback.assert_called_with(t.axrs.doRender, request)

        t.assertEqual(ret, server.NOT_DONE_YET)


class LoadCheckersTest(TestCase):
    """Test the LoadCheckers class."""

    @patch('{src}.checkers'.format(**PATH), spec=True)
    def test_getCredentialCheckers(self, checkers):
        pwdfile = "passwordfile"
        checker = checkers.FilePasswordDB.return_value

        expected = [checker]
        actual = getCredentialCheckers(pwdfile)

        checkers.FilePasswordDB.assert_called_with(pwdfile)
        self.assertEqual(actual, expected)
