from unittest import TestCase
from mock import patch, sentinel, call

from Products.ZenHub.zenhubworker import (
    _CumulativeWorkerStats,
    zenhubworker,
    IDLE,
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


class zenhubworkerTest(TestCase):

    @patch('{src}.metricWriter'.format(**PATH), autospec=True)
    @patch('{src}.TwistedMetricReporter'.format(**PATH), autospec=True)
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
        TwistedMetricReporter, metricWriter,
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
        zenhubworker.options.username = sentinel.username
        zenhubworker.options.password = sentinel.password
        zenhubworker.options.workernum = sentinel.workernum
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
            zhw.options.username, zhw.options.password
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
        TwistedMetricReporter.assert_called_with(
            metricWriter=metricWriter.return_value,
            tags={
                'zenoss_daemon': 'zenhub_worker_%s' % zhw.options.workernum,
                'zenoss_monitor': zhw.options.monitor,
                'internal': True
            }
        )
        metricreporter = TwistedMetricReporter.return_value
        t.assertEqual(zhw.metricreporter, metricreporter)
        zhw.metricreporter.start.assert_called_with()

        # Stop the metric reporter before the reactor shuts down
        # we have to pull the args from reactor.addSystemEventTrigger
        # because stopReporter is defined within the function
        args, kwargs = reactor.addSystemEventTrigger.call_args
        t.assertEqual((args[0], args[1]), ('before', 'shutdown'))
        stopReporter = args[2]
        zhw.metricreporter.stop.assert_not_called()
        stopReporter()
        zhw.metricreporter.stop.assert_called_with()
