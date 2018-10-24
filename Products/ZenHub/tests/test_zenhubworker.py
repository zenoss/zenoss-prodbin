from unittest import TestCase
from mock import patch, sentinel, call, Mock, create_autospec, MagicMock

from Products.ZenHub.zenhubworker import (
    _CumulativeWorkerStats,
    zenhubworker,
    IDLE,
    ContinuousProfiler,
    defaultdict,
    pickle,
    PB_PORT,
)


PATH = {'src': 'Products.ZenHub.zenhubworker'}


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


class zenhubworkerInitTest(TestCase):

    @patch('{src}.MetricManager'.format(**PATH), autospec=True)
    @patch('{src}.credentials'.format(**PATH), autospec=True)
    @patch('{src}.reactor'.format(**PATH), autospec=True)
    @patch('{src}.ReconnectingPBClientFactory'.format(**PATH), autospec=True)
    @patch('{src}.os'.format(**PATH), autospec=True)
    @patch('{src}.loadPlugins'.format(**PATH), autospec=True)
    @patch('{src}.Metrology'.format(**PATH), autospec=True)
    @patch('{src}.ContinuousProfiler'.format(**PATH), autospec=True)
    @patch('{src}.ZCmdBase.__init__'.format(**PATH), autospec=True)
    @patch('{src}.signal'.format(**PATH), autospec=True)
    def test___init__(
        t, signal, ZCmdBase__init__, ContinuousProfiler,  Metrology,
        loadPlugins, os, ReconnectingPBClientFactory, reactor, credentials,
        MetricManager,
    ):
        # ZCmdBase.__init__ sets options
        # Mock out attributes set by the parent class
        # Because these changes are made on the class, they must be reversable
        t.zenhubworker_patchers = [
            patch.object(zenhubworker, 'options', create=True),
            patch.object(zenhubworker, 'log', create=True),
            patch.object(zenhubworker, 'dmd', create=True),
        ]

        for patcher in t.zenhubworker_patchers:
            patcher.start()
            t.addCleanup(patcher.stop)

        zenhubworker.options = sentinel.options
        zenhubworker.options.profiling = True
        zenhubworker.options.hubhost = sentinel.hubhost
        zenhubworker.options.hubport = sentinel.hubport
        zenhubworker.options.hubusername = sentinel.hubusername
        zenhubworker.options.hubpassword = sentinel.hubpassword
        zenhubworker.options.workerid = sentinel.workerid
        zenhubworker.options.monitor = sentinel.monitor

        zhw = zenhubworker()

        signal.signal.assert_has_calls([
            call(signal.SIGUSR2, signal.SIG_IGN),
            call(signal.SIGUSR1, zhw.sighandler_USR1),
            call(signal.SIGUSR2, zhw.sighandler_USR2),
        ])
        # Base class init should be calld with super()
        ZCmdBase__init__.assert_called_with(zhw)
        # Optional Profiling
        ContinuousProfiler.assert_called_with('zenhubworker', log=zhw.log)
        t.assertEqual(zhw.profiler, ContinuousProfiler.return_value)
        zhw.profiler.start.assert_called_with()

        t.assertEqual(zhw.current, IDLE)
        t.assertEqual(zhw.currentStart, 0)
        Metrology.meter.assert_called_with("zenhub.workerCalls")
        t.assertEqual(zhw.numCalls, Metrology.meter.return_value)
        t.assertEqual(zhw.zem, zhw.dmd.ZenEventManager)
        loadPlugins.assert_called_with(zhw.dmd)
        t.assertEqual(zhw.services, {})
        # Establish connection to zenhub
        ReconnectingPBClientFactory.assert_called_with(pingPerspective=False)
        factory = ReconnectingPBClientFactory.return_value
        reactor.connectTCP.assert_called_with(
            zhw.options.hubhost,
            zhw.options.hubport,
            factory
        )
        credentials.UsernamePassword.assert_called_with(
            zhw.options.hubusername, zhw.options.hubpassword
        )
        t.assertEqual(factory.gotPerspective, zhw.gotPerspective)
        # The reactor will be stopped if the client looses its connection
        reactor.stop.assert_not_called()
        factory.clientConnectionLost()
        # callLater is pointless refactor it reactor.stop.assert_called_with()
        reactor.callLater.assert_called_with(0, reactor.stop)
        factory.setCredentials.assert_called_with(
            credentials.UsernamePassword.return_value
        )
        MetricManager.assert_called_with(
            daemon_tags={
                'zenoss_daemon': 'zenhub_worker_%s' % zhw.options.workerid,
                'zenoss_monitor': zhw.options.monitor,
                'internal': True
            }
        )
        t.assertEqual(zhw._metric_manager, MetricManager.return_value)
        zhw._metric_manager.start.assert_called_with()
        # trigger to shut down metric reporter before zenhubworker exits
        reactor.addSystemEventTrigger.assert_called_with(
            'before', 'shutdown', zhw._metric_manager.stop
        )


class zenhubworkerTest(TestCase):

    def setUp(t):
        # Patch out the __init__ method, due to excessive side-effects
        t.init_patcher = patch.object(
            zenhubworker, '__init__', autospec=True, return_value=None
        )
        t.init_patcher.start()
        t.addCleanup(t.init_patcher.stop)

        t.zhw = zenhubworker()
        t.zhw.options = Mock(
            name='options',
            spec_set=[
                'profiling', 'hubhost', 'hubport', 'hubusername',
                'hubpassword', 'workerid', 'monitor', 'call_limit'
            ]
        )
        t.zhw.log = Mock(name='log', spec_set=['error', 'debug', 'info'])

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
        super.assert_called_with(zenhubworker, t.zhw)
        super.return_value.sighandler_USR1.assert_called_with(signum, frame)

    def test_sighandler_USR2(t):
        args = sentinel.args
        t.zhw.reportStats = create_autospec(t.zhw.reportStats)

        t.zhw.sighandler_USR2(args)

        t.zhw.reportStats.assert_called_with()

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
        t.zhw.services = {(name, instance): service}
        isodate = isoDateTime.return_value

        t.zhw.reportStats()

        isoDateTime.assert_called_with(stats.lasttime)

        parsed_service_id = '{instance}/module_name'.format(**locals())
        average_time = stats.totaltime / stats.numoccurrences
        t.zhw.log.debug.assert_called_with(
            'Running statistics:\n'
            ' - {parsed_service_id: <49}{method: <32}'
            '{stats.numoccurrences: 9}{stats.totaltime: 13.2f}'
            '{average_time: 9.2f} {isodate}'.format(**locals())
        )

    @patch('{src}.reactor'.format(**PATH), autospec=True)
    def test_gotPerspective(t, reactor):
        '''register the worker with zenhub
        '''
        t.zhw.options.workerid = sentinel.workerId
        perspective = Mock(name='perspective', spec_set=['callRemote'])

        t.zhw.gotPerspective(perspective)

        perspective.callRemote.assert_called_with(
            'reportingForWork', t.zhw, workerId=t.zhw.options.workerid
        )
        # pull the internally defined function out of the return value
        deferred = perspective.callRemote.return_value
        args, kwargs = deferred.addErrback.call_args
        reportProblem = args[0]
        # the reportProblem errback stops the reactor
        reactor.stop.assert_not_called()
        reportProblem(sentinel.why)
        reactor.stop.assert_called_with()

    def test__getService(t):
        t.zhw.dmd = sentinel.dmd
        name = 'module.name'
        instance = 'collector_instance'
        service = sentinel.service
        t.zhw.services = {}
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
            ret = t.zhw._getService(name, instance)

        t.assertEqual(ret, service)
        t.assertEqual(ret, t.zhw.services[name, instance])
        Utils.importClass.assert_called_with(name)
        Utils.importClass.return_value.assert_called_with(t.zhw.dmd, instance)
        # also adds the callStats dict to the service
        t.assertEqual(service.callStats, defaultdict(_CumulativeWorkerStats))

    def test__getService_cached(t):
        name = 'module.name'
        instance = 'collector_instance'
        service = sentinel.service
        t.zhw.services = {(name, instance): service}

        ret = t.zhw._getService(name, instance)

        t.assertEqual(ret, t.zhw.services[name, instance])

    def test_remote_execute(t):
        '''RPC used to execute jobs
        Does way too many things
        chunking, retry, and stat logging needs to be tested separately
        '''
        service_name = 'service_name'
        service_fullname = 'module.for.{}'.format(service_name)
        instance = 'collector_instance'
        service = MagicMock(
            name='service', set_spec=['remote_method', 'callStats', 'callTime']
        )
        service.remote_method.return_value = sentinel.remote_method_result
        method = 'method'
        t.zhw.services = {(service_fullname, instance): service}
        args = ['sentinel.arg0', 'sentinel.arg1']
        kwargs = {'kwarg0': 'sentinel.kwarg0', 'kwarg1': 'sentinel.kwarg1'}
        pickled_args = pickle.dumps((args, kwargs))
        t.zhw.async_syncdb = create_autospec(t.zhw.async_syncdb)
        t.zhw.numCalls = Mock(name='numCalls', spec_set=['count', 'mark'])
        t.zhw.numCalls.count = 0
        t.zhw.options.call_limit = 10

        ret = t.zhw.remote_execute(
            service_fullname, instance, method, pickled_args
        )

        t.zhw.async_syncdb.assert_called_with()
        t.zhw.numCalls.mark.assert_called_with()
        service.remote_method.assert_called_with(*args, **kwargs)
        t.assertEqual(
            ret.result,
            [pickle.dumps(
                sentinel.remote_method_result, pickle.HIGHEST_PROTOCOL
            )]
        )
        t.assertEqual(t.zhw.current, IDLE)

    @patch('{src}.LastCallReturnValue'.format(**PATH), autospec=True)
    def test_remote_execute_handles_lastcall(t, LastCallReturnValue):
        t.zhw.async_syncdb = create_autospec(t.zhw.async_syncdb)
        t.zhw.numCalls = Mock(name='numCalls', spec_set=['count', 'mark'])
        service_name = 'service_name'
        service_fullname = 'module.for.{}'.format(service_name)
        instance = 'collector_instance'
        service = MagicMock(
            name='service', set_spec=['remote_method', 'callStats', 'callTime']
        )
        method = 'method'
        LastCallReturnValue.return_value = sentinel.last_remote_method_result
        t.zhw.services = {(service_fullname, instance): service}
        args = ['sentinel.arg0', 'sentinel.arg1']
        kwargs = {'kwarg0': 'sentinel.kwarg0', 'kwarg1': 'sentinel.kwarg1'}
        pickled_args = pickle.dumps((args, kwargs))
        t.zhw.numCalls.count = 10
        t.zhw.options.call_limit = 10

        ret = t.zhw.remote_execute(
            service_fullname, instance, method, pickled_args
        )

        LastCallReturnValue.assert_called_with(
            service.remote_method.return_value
        )
        t.assertEqual(
            ret.result,
            [pickle.dumps(
                sentinel.last_remote_method_result, pickle.HIGHEST_PROTOCOL
            )]
        )

    @patch('{src}.reactor'.format(**PATH), autospec=True)
    def test__shutdown(t, reactor):
        t.zhw.reportStats = create_autospec(t.zhw.reportStats)
        t.zhw.profiler = Mock(name='profiler', spec_set=['stop'])
        t.zhw.options.profiling = True

        t.zhw._shutdown()

        t.zhw.reportStats.assert_called_with()
        t.zhw.profiler.stop.assert_called_with()
        reactor.stop.assert_called_with()

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
