##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from unittest import TestCase
from mock import patch, sentinel, call, Mock, create_autospec, ANY, MagicMock

from Products.ZenHub.zenhubworker import (
    _CumulativeWorkerStats,
    ZenHubWorker,
    ZenHubClient,
    PingZenHub,
    ServiceReferenceFactory,
    ServiceReference,
    RemoteConflictError,
    ZCmdBase,
    IDLE,
    ContinuousProfiler,
    PB_PORT,
    RemoteBadMonitor,
    UnknownServiceError,
    pb,
    defer,
)


PATH = {'src': 'Products.ZenHub.zenhubworker'}


class ZenHubWorkerTest(TestCase):

    def setUp(t):
        # Patch out the ZCmdBase __init__ method
        t.ZCmdBase_patcher = patch.object(
            ZCmdBase, '__init__', autospec=True, return_value=None
        )
        t.ZCmdBase__init__ = t.ZCmdBase_patcher.start()
        t.addCleanup(t.ZCmdBase_patcher.stop)

        # Mock out attributes set by ZCmdBase
        t.zcmdbase_patchers = {
            'dmd': patch.object(ZenHubWorker, 'dmd', create=True),
            'log': patch.object(ZenHubWorker, 'log', create=True),
            'options': patch.object(ZenHubWorker, 'options', create=True),
        }
        for name, patcher in t.zcmdbase_patchers.items():
            setattr(t, name, patcher.start())
            t.addCleanup(patcher.stop)

        # ZenHubWorker.options = sentinel.options
        t.options.profiling = True
        t.options.hubhost = "localhost"
        t.options.hubport = 8765
        t.options.hubusername = sentinel.hubusername
        t.options.hubpassword = sentinel.hubpassword
        t.options.workerid = sentinel.workerid
        t.options.monitor = sentinel.monitor

        # Patch external dependencies
        needs_patching = [
            'ContinuousProfiler',
            'HubServiceRegistry',
            'MetricManager',
            'Metrology',
            'loadPlugins',
            'ServiceReferenceFactory',
            'UsernamePassword',
            'clientFromString',
            'ZenHubClient',
            'reactor',
        ]
        t.patchers = {}
        for target in needs_patching:
            patched = patch(
                '{src}.{target}'.format(target=target, **PATH), autospec=True
            )
            t.patchers[target] = patched
            setattr(t, target, patched.start())
            t.addCleanup(patched.stop)

        t.zhw = ZenHubWorker(t.reactor)

    def test___init__(t):
        t.ZCmdBase__init__.assert_called_with(t.zhw)

        # Optional Profiling
        t.ContinuousProfiler.assert_called_with('ZenHubWorker', log=t.zhw.log)
        t.assertEqual(t.zhw.profiler, t.ContinuousProfiler.return_value)
        t.zhw.profiler.start.assert_called_with()
        t.reactor.addSystemEventTrigger.assert_called_once_with(
            "before", "shutdown", t.zhw.profiler.stop
        )

        t.assertEqual(t.zhw.current, IDLE)
        t.assertEqual(t.zhw.currentStart, 0)
        t.Metrology.meter.assert_called_with("zenhub.workerCalls")
        t.assertEqual(t.zhw.numCalls, t.Metrology.meter.return_value)

        t.assertEqual(t.zhw.zem, t.zhw.dmd.ZenEventManager)
        t.loadPlugins.assert_called_with(t.zhw.dmd)

        t.ServiceReferenceFactory.assert_called_once_with(t.zhw)
        t.HubServiceRegistry.assert_called_once_with(
            t.dmd, t.ServiceReferenceFactory.return_value
        )
        t.assertEqual(
            t.HubServiceRegistry.return_value, t.zhw._ZenHubWorker__registry
        )

        t.UsernamePassword.assert_called_once_with(
            t.zhw.options.hubusername, t.zhw.options.hubpassword
        )
        t.clientFromString.assert_called_once_with(
            t.reactor,
            "tcp:%s:%s" % (t.zhw.options.hubhost, t.zhw.options.hubport)
        )
        t.ZenHubClient.assert_called_once_with(
            t.reactor, t.clientFromString.return_value,
            t.UsernamePassword.return_value, t.zhw, 10.0
        )
        t.assertEqual(t.ZenHubClient.return_value, t.zhw._ZenHubWorker__client)

        t.MetricManager.assert_called_with(
            daemon_tags={
                'zenoss_daemon': 'zenhub_worker_%s' % t.zhw.options.workerid,
                'zenoss_monitor': t.zhw.options.monitor,
                'internal': True
            }
        )
        t.assertEqual(t.zhw._metric_manager, t.MetricManager.return_value)

    @patch("{src}.signal".format(**PATH), autospec=True)
    def test_start(t, signal):
        signal.SIGUSR1 = sentinel.SIGUSR1
        signal.SIGUSR2 = sentinel.SIGUSR2

        t.zhw.start()

        signal.signal.assert_has_calls([
            call(signal.SIGUSR1, t.zhw.sighandler_USR1),
            call(signal.SIGUSR2, t.zhw.sighandler_USR2),
        ])

        t.ZenHubClient.return_value.start.assert_called_once_with()
        t.MetricManager.return_value.start.assert_called_once_with()

        t.reactor.addSystemEventTrigger.assert_has_calls([
            call("before", "shutdown", t.ZenHubClient.return_value.stop),
            call("before", "shutdown", t.MetricManager.return_value.stop),
        ])

    def test_audit(t):
        '''does nothing
        '''
        action = sentinel.action
        t.zhw.audit(action)

    @patch('{src}.super'.format(**PATH))
    def test_sighandler_USR1(t, super):
        t.zhw.options.profiling = True
        t.zhw.profiler = Mock(ContinuousProfiler, name='profiler')
        signum, frame = sentinel.signum, sentinel.frame

        t.zhw.sighandler_USR1(signum, frame)

        t.zhw.profiler.dump_stats.assert_called_with()
        super.assert_called_with(ZenHubWorker, t.zhw)
        super.return_value.sighandler_USR1.assert_called_with(signum, frame)

    def test_sighandler_USR2(t):
        args = sentinel.args
        t.zhw.reportStats = create_autospec(t.zhw.reportStats)

        t.zhw.sighandler_USR2(args)

        t.zhw.reportStats.assert_called_with()

    def test_work_started(t):
        startTime = sentinel.startTime

        t.zhw.work_started(startTime)

        t.assertEqual(t.zhw.currentStart, startTime)
        t.zhw.numCalls.mark.assert_called_once_with()

    @patch("{src}.IDLE".format(**PATH))
    def test_work_finished_no_shutdown(t, idle):
        duration = sentinel.duration
        method = sentinel.method
        t.zhw.numCalls.count = 1
        t.zhw.options.call_limit = 5

        t.zhw.work_finished(duration, method)

        t.assertEqual(idle, t.zhw.current)
        t.assertEqual(0, t.zhw.currentStart)
        t.reactor.callLater.assert_not_called()

    @patch("{src}.IDLE".format(**PATH))
    def test_work_finished_with_shutdown(t, idle):
        duration = sentinel.duration
        method = sentinel.method
        t.zhw.numCalls.count = 5
        t.zhw.options.call_limit = 5

        t.zhw.work_finished(duration, method)

        t.assertEqual(idle, t.zhw.current)
        t.assertEqual(0, t.zhw.currentStart)
        t.reactor.callLater.assert_called_once_with(0, t.zhw._shutdown)

    @patch('{src}.isoDateTime'.format(**PATH), autospec=True)
    @patch('{src}.time'.format(**PATH), autospec=True)
    def test_reportStats(t, time, isoDateTime):
        '''Metric Reporting Function. Log various statistics on services
        as a general rule, do not test individual log messages, just log format
        this function is difficult to read and should be refactored
        '''
        t.zhw.current = sentinel.current_job
        t.zhw.options.workerid = 1
        t.zhw.currentStart = 0
        time.time.return_value = 7
        name = 'module.module_name'
        instance = 'collector_instance'
        service = sentinel.service
        method = 'method_name'
        stats = sentinel.stats
        stats.numoccurrences = 9
        stats.totaltime = 54
        stats.lasttime = 555
        service.callStats = {method: stats}
        t.zhw._ZenHubWorker__registry = {
            (name, instance): service
        }
        isodate = isoDateTime.return_value

        t.zhw.reportStats()

        isoDateTime.assert_called_with(stats.lasttime)

        parsed_service_id = '{instance}/module_name'.format(**locals())
        average_time = stats.totaltime / stats.numoccurrences
        t.zhw.log.info.assert_called_with(
            'Running statistics:\n'
            ' - {parsed_service_id: <49}{method: <32}'
            '{stats.numoccurrences: 9}{stats.totaltime: 13.2f}'
            '{average_time: 9.2f} {isodate}'.format(**locals())
        )

    def test_remote_reportStatus(t):
        t.zhw.reportStats = Mock(t.zhw.reportStats)
        t.zhw.remote_reportStatus()
        t.zhw.reportStats.assert_called_once_with()

    def test_remote_reportStatus_failure(t):
        t.zhw.reportStats = Mock(t.zhw.reportStats)
        t.zhw.reportStats.side_effect = ValueError("boom")

        t.zhw.remote_reportStatus()

        t.zhw.reportStats.assert_called_once_with()
        t.zhw.log.exception.assert_called_once_with(ANY)

    def test_remote_getService(t):
        name = "service"
        monitor = "monitor"
        registry = t.HubServiceRegistry.return_value
        expected = registry.getService.return_value

        actual = t.zhw.remote_getService(name, monitor)

        t.assertEqual(expected, actual)
        registry.getService.assert_called_once_with(name, monitor)

    def test_remote_getService_bad_monitor(t):
        name = "service"
        monitor = "bad"
        registry = t.HubServiceRegistry.return_value

        errorMessage = "boom"
        tb = Mock()
        registry.getService.side_effect = RemoteBadMonitor(errorMessage, tb)

        with t.assertRaises(RemoteBadMonitor):
            t.zhw.remote_getService(name, monitor)

        registry.getService.assert_called_once_with(name, monitor)

    def test_remote_getService_unknown_service(t):
        name = "bad"
        monitor = "monitor"
        registry = t.HubServiceRegistry.return_value
        registry.getService.side_effect = UnknownServiceError("boom")

        with t.assertRaises(UnknownServiceError):
            t.zhw.remote_getService(name, monitor)

        registry.getService.assert_called_once_with(name, monitor)
        t.zhw.log.error.assert_has_calls([ANY])

    def test_remote_getService_general_error(t):
        name = "bad"
        monitor = "monitor"
        error = ValueError("boom")
        registry = t.HubServiceRegistry.return_value
        registry.getService.side_effect = error

        with t.assertRaises(pb.Error):
            t.zhw.remote_getService(name, monitor)
            registry.getService.assert_called_once_with(name, monitor)
            t.zhw.log.exception.assert_has_calls([ANY])

    def test__shutdown(t):
        t.zhw._shutdown()
        t.reactor.stop.assert_called_with()

    @patch('{src}.ZCmdBase'.format(**PATH))
    def test_buildOptions(t, ZCmdBase):
        '''After initialization, the ZenHubWorker instance should have
        options parsed from its buildOptions method
        assertions based on default options
        '''
        # this should call buildOptions on parent classes, up the tree
        # currently calls an ancestor class directly
        # parser expected to be added by CmdBase.buildParser
        from optparse import OptionParser
        t.zhw.parser = OptionParser()

        t.zhw.buildOptions()
        t.zhw.options, args = t.zhw.parser.parse_args()

        ZCmdBase.buildOptions.assert_called_with(t.zhw)
        t.assertEqual(t.zhw.options.hubhost, 'localhost')
        t.assertEqual(t.zhw.options.hubport, PB_PORT)
        t.assertEqual(t.zhw.options.hubusername, 'admin')
        t.assertEqual(t.zhw.options.hubpassword, 'zenoss')
        t.assertEqual(t.zhw.options.call_limit, 200)
        t.assertEqual(t.zhw.options.profiling, False)
        t.assertEqual(t.zhw.options.monitor, 'localhost')
        t.assertEqual(t.zhw.options.workerid, 0)


class ZenHubClientTest(TestCase):

    def setUp(t):
        # t.reactor = Mock()
        t.endpoint = sentinel.endpoint
        t.credentials = Mock()
        t.worker = Mock()
        t.timeout = 10

        # Patch external dependencies
        needs_patching = [
            'pb.PBClientFactory',
            'clientFromString',
            'ClientService',
            'ConnectedToZenHubSignalFile',
            'PingZenHub',
            'backoffPolicy',
            'getLogger',
            'reactor',
            'task.LoopingCall',
        ]
        t.patchers = {}
        for target in needs_patching:
            patched = patch(
                '{src}.{target}'.format(target=target, **PATH), autospec=True
            )
            t.patchers[target] = patched
            name = target.rpartition('.')[-1]
            setattr(t, name, patched.start())
            t.addCleanup(patched.stop)

        t.zhc = ZenHubClient(
            t.reactor, t.endpoint, t.credentials, t.worker, t.timeout
        )

    def test___init__(t):
        t.assertEqual(t.zhc._ZenHubClient__reactor, t.reactor)
        t.assertEqual(t.zhc._ZenHubClient__endpoint, t.endpoint)
        t.assertEqual(t.zhc._ZenHubClient__credentials, t.credentials)
        t.assertEqual(t.zhc._ZenHubClient__worker, t.worker)
        t.assertEqual(t.zhc._ZenHubClient__timeout, t.timeout)

        t.assertEqual(t.zhc._ZenHubClient__stopping, False)
        t.assertEqual(t.zhc._ZenHubClient__pinger, None)
        t.assertEqual(t.zhc._ZenHubClient__service, None)
        t.assertEqual(t.zhc._ZenHubClient__log, t.getLogger.return_value)
        t.assertEqual(
            t.zhc._ZenHubClient__signalFile,
            t.ConnectedToZenHubSignalFile.return_value
        )

    @patch.object(ZenHubClient, "_ZenHubClient__prepForConnection")
    def test_start(t, prepForConnection):
        t.zhc._ZenHubClient__stopping = True

        t.zhc.start()

        t.assertEqual(t.zhc._ZenHubClient__stopping, False)
        t.backoffPolicy.assert_called_once_with(initialDelay=0.5, factor=3.0)
        t.ClientService.assert_called_once_with(
            t.endpoint, t.PBClientFactory.return_value,
            retryPolicy=t.backoffPolicy.return_value
        )
        service = t.ClientService.return_value
        service.startService.assert_called_once_with()
        prepForConnection.assert_called_once_with()

    @patch.object(ZenHubClient, "_ZenHubClient__reset")
    def test_stop(t, reset):
        t.zhc.stop()
        t.assertEqual(t.zhc._ZenHubClient__stopping, True)
        reset.assert_called_once_with()

    @patch.object(ZenHubClient, "_ZenHubClient__reset")
    @patch.object(ZenHubClient, "start")
    def test_restart(t, start, reset):
        t.zhc.restart()
        reset.assert_called_once_with()
        start.assert_called_once_with()

    def test___reset_not_started(t):
        signalFile = t.ConnectedToZenHubSignalFile.return_value
        service = t.ClientService.return_value
        pinger = t.LoopingCall.return_value

        t.zhc._ZenHubClient__reset()

        signalFile.remove.assert_called_once_with()
        service.stopService.assert_not_called()
        pinger.stop.assert_not_called()

    def test___reset_after_start(t):
        signalFile = t.ConnectedToZenHubSignalFile.return_value
        service = t.ClientService.return_value
        t.zhc._ZenHubClient__service = service
        pinger = t.LoopingCall.return_value
        t.zhc._ZenHubClient__pinger = pinger

        t.zhc._ZenHubClient__reset()

        signalFile.remove.assert_called_once_with()
        service.stopService.assert_called_once_with()
        pinger.stop.assert_called_once_with()
        t.assertIsNone(t.zhc._ZenHubClient__pinger)
        t.assertIsNone(t.zhc._ZenHubClient__service)

    @patch.object(ZenHubClient, "_ZenHubClient__connected")
    @patch.object(ZenHubClient, "_ZenHubClient__notConnected")
    def test___prepForConnection(t, notConnected, connected):
        service = t.ClientService.return_value
        t.zhc._ZenHubClient__service = service
        d = t.zhc._ZenHubClient__service.whenConnected.return_value

        t.zhc._ZenHubClient__prepForConnection()

        service.whenConnected.assert_called_once_with()
        d.addCallbacks.assert_called_once_with(connected, notConnected)

    def test___prepForConnection_after_stopping(t):
        service = t.ClientService.return_value
        t.zhc._ZenHubClient__service = service
        t.zhc._ZenHubClient__stopping = True

        t.zhc._ZenHubClient__prepForConnection()

        service.whenConnected.assert_not_called()

    @patch.object(ZenHubClient, "_ZenHubClient__prepForConnection")
    def test___disconnected_not_connected(t, prepForConnection):
        signalFile = t.ConnectedToZenHubSignalFile.return_value

        t.zhc._ZenHubClient__disconnected()

        prepForConnection.assert_called_once_with()
        signalFile.remove.assert_called_once_with()

    @patch.object(ZenHubClient, "_ZenHubClient__prepForConnection")
    def test___disconnected_after_connection(t, prepForConnection):
        signalFile = t.ConnectedToZenHubSignalFile.return_value
        pinger = t.LoopingCall.return_value
        t.zhc._ZenHubClient__pinger = pinger

        t.zhc._ZenHubClient__disconnected()

        prepForConnection.assert_called_once_with()
        signalFile.remove.assert_called_once_with()
        pinger.stop.assert_called_once_with()
        t.assertIsNone(t.zhc._ZenHubClient__pinger)

    @patch.object(ZenHubClient, "restart")
    @patch.object(ZenHubClient, "_ZenHubClient__login")
    def test___connected_no_connection(t, login, restart):
        broker = MagicMock(spec=["transport"])
        broker.transport.mock_add_spec([""])

        t.zhc._ZenHubClient__connected(broker)
        restart.assert_called_once_with()
        login.assert_not_called()

    @patch.object(ZenHubClient, "_ZenHubClient__login")
    @patch.object(ZenHubClient, "_ZenHubClient__pingFail")
    @patch.object(ZenHubClient, "restart")
    @patch("{src}.setKeepAlive".format(**PATH), autospec=True)
    def test___connected(t, setKeepAlive, restart, pingFail, login):
        broker = MagicMock(spec=["transport", "notifyOnDisconnect"])
        broker.transport.mock_add_spec(["socket"])
        zenhub = login.return_value
        pinger = t.LoopingCall.return_value
        pinger_deferred = pinger.start.return_value

        t.zhc._ZenHubClient__connected(broker)

        login.assert_called_once_with(broker)
        zenhub.callRemote.assert_called_once_with(
            "reportingForWork",
            t.zhc._ZenHubClient__worker,
            workerId=t.zhc._ZenHubClient__worker.instanceId
        )
        t.LoopingCall.assert_called_once_with(t.PingZenHub.return_value)
        t.assertEqual(t.zhc._ZenHubClient__pinger, pinger)
        pinger.start.assert_called_once_with(
            t.zhc._ZenHubClient__timeout, now=False
        )
        pinger_deferred.addErrback.assert_called_once_with(pingFail)
        t.zhc._ZenHubClient__signalFile.touch.assert_called_once_with()
        broker.notifyOnDisconnect.assert_called_once_with(
            t.zhc._ZenHubClient__disconnected
        )

        t.zhc._ZenHubClient__signalFile.remove.assert_not_called()
        restart.assert_not_called()
        t.reactor.stop.assert_not_called()

    @patch.object(ZenHubClient, "_ZenHubClient__login")
    def test___connected_login_failure(t, login):
        broker = MagicMock(spec=["transport"])
        broker.transport.mock_add_spec(["socket"])
        ex = ValueError("boom")
        login.side_effect = ex

        t.zhc._ZenHubClient__connected(broker)

        login.assert_called_once_with(broker)
        t.zhc._ZenHubClient__log.error.assert_called_once_with(
            ANY, type(ex), ex
        )
        t.zhc._ZenHubClient__signalFile.remove.assert_called_once_with()
        t.reactor.stop.assert_called_once_with()

    @patch.object(ZenHubClient, "_ZenHubClient__login")
    @patch.object(ZenHubClient, "restart")
    def test___connected_login_timeout(t, restart, login):
        broker = MagicMock(spec=["transport"])
        broker.transport.mock_add_spec(["socket"])
        ex = defer.CancelledError()
        login.side_effect = ex

        t.zhc._ZenHubClient__connected(broker)

        login.assert_called_once_with(broker)
        t.zhc._ZenHubClient__log.error.assert_called_once_with(ANY)
        restart.assert_called_once_with()

        t.zhc._ZenHubClient__signalFile.remove.assert_not_called()
        t.zhc._ZenHubClient__signalFile.touch.assert_not_called()
        t.reactor.stop.assert_not_called()

    @patch.object(ZenHubClient, "_ZenHubClient__login")
    @patch.object(ZenHubClient, "restart")
    def test___connected_reportingForWork_failure(t, restart, login):
        broker = MagicMock(spec=["transport"])
        broker.transport.mock_add_spec(["socket"])
        zenhub = login.return_value
        ex = ValueError("boom")
        zenhub.callRemote.side_effect = ex

        t.zhc._ZenHubClient__connected(broker)

        login.assert_called_once_with(broker)
        zenhub.callRemote.assert_called_once_with(
            "reportingForWork",
            t.zhc._ZenHubClient__worker,
            workerId=t.zhc._ZenHubClient__worker.instanceId
        )
        t.zhc._ZenHubClient__log.error.assert_called_once_with(
            ANY, type(ex), ex
        )
        t.zhc._ZenHubClient__signalFile.remove.assert_called_once_with()
        t.reactor.stop.assert_called_once_with()

    def test___login(t):
        broker = MagicMock(spec=["factory"])
        broker.factory.mock_add_spec(["login"])
        expected = defer.Deferred()
        broker.factory.login.return_value = expected
        timeout = t.reactor.callLater.return_value
        timeout.active.return_value = True

        actual = t.zhc._ZenHubClient__login(broker)
        actual.callback("OK")

        t.assertEqual(expected, actual)
        broker.factory.login.assert_called_once_with(
            t.zhc._ZenHubClient__credentials, t.zhc._ZenHubClient__worker
        )
        t.reactor.callLater.assert_called_once_with(
            t.zhc._ZenHubClient__timeout, actual.cancel
        )
        timeout.active.assert_called_once_with()
        timeout.cancel.assert_called_once_with()

    def test___login_timeout(t):
        broker = MagicMock(spec=["factory"])
        broker.factory.mock_add_spec(["login"])
        expected = defer.Deferred()
        broker.factory.login.return_value = expected
        timeout = t.reactor.callLater.return_value
        timeout.active.return_value = False

        actual = t.zhc._ZenHubClient__login(broker)
        actual.addErrback(lambda x: None)  # don't propate the error
        actual.cancel()

        t.assertEqual(expected, actual)
        broker.factory.login.assert_called_once_with(
            t.zhc._ZenHubClient__credentials, t.zhc._ZenHubClient__worker
        )
        t.reactor.callLater.assert_called_once_with(
            t.zhc._ZenHubClient__timeout, actual.cancel
        )
        timeout.active.assert_called_once_with()
        timeout.cancel.assert_not_called()


class PingZenHubTest(TestCase):

    def setUp(t):
        t.zenhub = Mock()
        t.client = Mock()
        # Patch external dependencies
        needs_patching = [
            'getLogger',
        ]
        t.patchers = {}
        for target in needs_patching:
            patched = patch(
                '{src}.{target}'.format(target=target, **PATH), autospec=True
            )
            t.patchers[target] = patched
            name = target.rpartition('.')[-1]
            setattr(t, name, patched.start())
            t.addCleanup(patched.stop)

        t.pzh = PingZenHub(t.zenhub, t.client)

    def test___init__(t):
        logger = t.getLogger.return_value

        t.assertEqual(t.zenhub, t.pzh._PingZenHub__zenhub)
        t.assertEqual(t.client, t.pzh._PingZenHub__client)
        t.assertEqual(logger, t.pzh._PingZenHub__log)
        t.getLogger.assert_called_once_with(t.pzh)

    def test___call__(t):
        t.pzh.__call__()
        t.zenhub.callRemote.assert_called_once_with("ping")
        t.client.restart.assert_not_called()

    def test___call__failed(t):
        logger = t.getLogger.return_value
        ex = ValueError("boom")
        t.zenhub.callRemote.side_effect = ex

        t.pzh.__call__()

        logger.error.assert_called_once_with(ANY, ex)
        t.client.restart.assert_called_once_with()


class ServiceReferenceFactoryTest(TestCase):

    @patch("{src}.ServiceReference".format(**PATH), autospec=True)
    def test_build(t, ServiceReference):
        worker = sentinel.worker
        factory = ServiceReferenceFactory(worker)
        service = sentinel.service
        name = sentinel.name
        monitor = sentinel.monitor

        result = factory.build(service, name, monitor)

        ServiceReference.assert_called_once_with(
            service, name, monitor, worker
        )
        t.assertEqual(ServiceReference.return_value, result)


class ServiceReferenceTest(TestCase):

    def setUp(t):
        t._CumulativeWorkerStats_patcher = patch(
            "{src}._CumulativeWorkerStats".format(**PATH), autospec=True
        )
        t._CumulativeWorkerStats = t._CumulativeWorkerStats_patcher.start()
        t.addCleanup(t._CumulativeWorkerStats_patcher.stop)

        t.service = Mock(spec_set=["remoteMessageReceived", "callTime"])
        t.worker = Mock(ZenHubWorker)
        t.name = "path.to.service"
        t.monitor = sentinel.monitor
        t.ref = ServiceReference(t.service, t.name, t.monitor, t.worker)

    def test_callStats_property(t):
        t.assertIsInstance(t.ref.callStats, dict)
        t.assertEqual(0, len(t.ref.callStats))

    def test_name_property(t):
        t.assertEqual(t.name, t.ref.name)

    def test_monitor_property(t):
        t.assertEqual(t.monitor, t.ref.monitor)

    def test_remoteMessageReceived(t):
        broker = sentinel.broker
        message = sentinel.message
        args = sentinel.args
        kwargs = sentinel.kwargs

        t.worker.async_syncdb.side_effect = [None]

        expected = t.service.remoteMessageReceived.return_value

        with patch.object(t.ref, "_ServiceReference__update_stats") as p:
            d = t.ref.remoteMessageReceived(broker, message, args, kwargs)

            t.assertEqual(expected, d.result)
            p.assert_called_once_with(message)
            t.worker.async_syncdb.assert_called_once_with()
            t.service.remoteMessageReceived.assert_called_once_with(
                broker, message, args, kwargs
            )

    def test_remoteMessageReceived_one_conflict(t):
        broker = sentinel.broker
        method = sentinel.method
        args = sentinel.args
        kwargs = sentinel.kwargs

        mesg = sentinel.mesg
        tb = sentinel.tb
        error = RemoteConflictError(mesg, tb)
        t.worker.async_syncdb.side_effect = [error]

        expected = t.service.remoteMessageReceived.return_value

        with patch.object(t.ref, "_ServiceReference__update_stats") as p:
            d = t.ref.remoteMessageReceived(broker, method, args, kwargs)

            t.assertEqual(expected, d.result)
            p.assert_called_once_with(method)
            t.worker.async_syncdb.assert_called_once_with()
            t.service.remoteMessageReceived.assert_called_once_with(
                broker, method, args, kwargs
            )

    def test_remoteMessageReceived_three_conflicts(t):
        broker = sentinel.broker
        method = sentinel.method
        args = sentinel.args
        kwargs = sentinel.kwargs

        mesg = sentinel.mesg
        tb = sentinel.tb
        error = RemoteConflictError(mesg, tb)
        t.worker.async_syncdb.side_effect = [error, error]

        expected = sentinel.expected
        t.service.remoteMessageReceived.side_effect = [error, expected]

        with patch.object(t.ref, "_ServiceReference__update_stats") as p:
            t.ref.debug = True
            d = t.ref.remoteMessageReceived(broker, method, args, kwargs)

            t.assertEqual(expected, d.result)
            p.assert_called_once_with(method)
            t.worker.async_syncdb.assert_has_calls([call(), call()])
            t.service.remoteMessageReceived.assert_has_calls([
                call(broker, method, args, kwargs),
                call(broker, method, args, kwargs),
            ])

    def test_remoteMessageReceived_last_retry(t):
        broker = sentinel.broker
        method = sentinel.method
        args = sentinel.args
        kwargs = sentinel.kwargs

        mesg = sentinel.mesg
        tb = sentinel.tb
        error = RemoteConflictError(mesg, tb)
        expected = sentinel.expected
        t.service.remoteMessageReceived.side_effect = [
            error, error, error, error, expected
        ]

        with patch.object(t.ref, "_ServiceReference__update_stats") as p:
            t.ref.debug = True
            d = t.ref.remoteMessageReceived(broker, method, args, kwargs)

            t.assertEqual(expected, d.result)
            p.assert_called_once_with(method)
            t.worker.async_syncdb.assert_has_calls([
                call(), call(), call(), call()
            ])
            t.service.remoteMessageReceived.assert_has_calls([
                call(broker, method, args, kwargs),
                call(broker, method, args, kwargs),
                call(broker, method, args, kwargs),
                call(broker, method, args, kwargs),
                call(broker, method, args, kwargs),
            ])

    def test_remoteMessageReceived_raises_RemoteConflictError(t):
        broker = sentinel.broker
        method = sentinel.method
        args = sentinel.args
        kwargs = sentinel.kwargs

        mesg = sentinel.mesg
        tb = sentinel.tb
        error = RemoteConflictError(mesg, tb)
        t.service.remoteMessageReceived.side_effect = [
            error, error, error, error, error
        ]

        class Capture(object):
            result = None

            def err(self, err):
                self.result = err.trap(RemoteConflictError)

        with patch.object(t.ref, "_ServiceReference__update_stats") as p:
            t.ref.debug = True

            handler = Capture()
            d = t.ref.remoteMessageReceived(broker, method, args, kwargs)
            d.addErrback(handler.err)

            p.assert_called_once_with(method)
            t.worker.async_syncdb.assert_has_calls([
                call(), call(), call(), call()
            ])
            t.service.remoteMessageReceived.assert_has_calls([
                call(broker, method, args, kwargs),
                call(broker, method, args, kwargs),
                call(broker, method, args, kwargs),
                call(broker, method, args, kwargs),
                call(broker, method, args, kwargs),
            ])
            t.assertEqual(RemoteConflictError, handler.result)

    def test_remoteMessageReceived_raises_other_exception(t):
        broker = sentinel.broker
        method = sentinel.method
        args = sentinel.args
        kwargs = sentinel.kwargs

        error = ValueError("boom")
        t.service.remoteMessageReceived.side_effect = error

        class Capture(object):
            result = None

            def err(self, err):
                self.result = err.trap(ValueError)

        with patch.object(t.ref, "_ServiceReference__update_stats") as p:
            t.ref.debug = True

            handler = Capture()
            d = t.ref.remoteMessageReceived(broker, method, args, kwargs)
            d.addErrback(handler.err)

            p.assert_called_once_with(method)
            t.worker.async_syncdb.assert_called_once_with()
            t.service.remoteMessageReceived.assert_called_once_with(
                broker, method, args, kwargs
            )
            t.assertEqual(ValueError, handler.result)

    @patch("{src}.time".format(**PATH), autospec=True)
    def test___update_stats(t, time):
        start = 15
        finish = 20
        time.time.side_effect = [start, finish]
        method = "method"
        expected_current = "service/method"
        stats = Mock(_CumulativeWorkerStats)
        t.service.callTime = 0

        with patch.dict(t.ref.callStats, method=stats):
            with t.ref._ServiceReference__update_stats(method) as p:
                t.assertEqual(t.service, p)
                t.assertEqual(expected_current, t.worker.current)
                t.worker.work_started.assert_called_once_with(start)

            stats.addOccurrence.assert_called_once_with(5, finish)
            t.assertEqual(5, t.service.callTime)
            t.worker.work_finished.assert_called_once_with(5, method)


class _CumulativeWorkerStatsTest(TestCase):

    def test___init__(t):
        cws = _CumulativeWorkerStats()
        t.assertEqual(cws.numoccurrences, 0)
        t.assertEqual(cws.totaltime, 0.0)
        t.assertEqual(cws.lasttime, 0)

    @patch('{src}.time'.format(**PATH), autospec=True)
    def test_addOccurrence(t, time):
        time.time.side_effect = [sentinel.t0, sentinel.t1]
        cws = _CumulativeWorkerStats()

        cws.addOccurrence(10)

        t.assertEqual(cws.numoccurrences, 1)
        t.assertEqual(cws.totaltime, 10.0)
        t.assertEqual(cws.lasttime, sentinel.t0)

        cws.addOccurrence(100)

        t.assertEqual(cws.numoccurrences, 2)
        t.assertEqual(cws.totaltime, 110.0)
        t.assertEqual(cws.lasttime, sentinel.t1)
