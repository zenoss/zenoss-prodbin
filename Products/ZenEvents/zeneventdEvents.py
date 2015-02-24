##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import pkg_resources
from zenoss.protocols.eventlet.amqp import register_eventlet
from twisted.internet import reactor
from zope.component import adapter, getGlobalSiteManager
from Products.ZenEvents.zeneventd import ZenEventD
from Products.ZenEvents.daemonlifecycle import DaemonCreatedEvent, DaemonStartRunEvent
from Products.ZenEvents.daemonlifecycle import SigTermEvent, SigUsr1Event, BuildOptionsEvent
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenCollector.utils.workers import ProcessWorkers, workersBuildOptions, exec_worker
from Products.ZenCollector.utils.maintenance import maintenanceBuildOptions
from Products.ZenUtils.Utils import zenPath

@adapter(ZenEventD, SigTermEvent)
def onSigTerm(daemon, event):
    if daemon.options.daemon:
        daemon._workers.shutdown()

@adapter(ZenEventD, SigUsr1Event)
def onSigUsr1(daemon, event):
    if daemon.options.daemon:
        daemon._workers.sendSignal(event.signum)

@adapter(ZCmdBase, BuildOptionsEvent)
def onBuildOptions(daemon, event):
    workersBuildOptions(daemon.parser, default=1)
    maintenanceBuildOptions(daemon.parser)
    # zeneventdWorker.py parser options (zeneventd.conf)
    ######################################################
    daemon.parser.add_option('--messagesperworker', dest='messagesPerWorker', default=1, type="int",
                help='Number of RabbitMQ messages each worker gets from the queue at any given time.'
                'Increasing causes some events to be processed out of order.')
    # zeneventd.py parser options (zeneventd.conf)
    ######################################################
    daemon.parser.add_option('--synceveryevent', dest='SYNC_EVERY_EVENT', action="store_true", default=False,
                help='sync() before  every event (default is sync() no more often than every 1/2 second.')
    daemon.parser.add_option('--maxpickle', dest='maxpickle', default=100, type="int",
                help='Sets the number of pickle files in var/zeneventd/failed_transformed_events.')
    daemon.parser.add_option('--pickledir', dest='pickledir', default=zenPath('var/zeneventd/failed_transformed_events'),
                type="string", help='Sets the path to save pickle files.')
    daemon.parser.add_option('--sloweventthreshold', dest='slowEventThreshold', default=5.0, type='float',
                help='threshold (in seconds) for logging slow processMessage calls')
    daemon.parser.add_option('--slowsegmentthreshold', dest='slowSegmentThreshold', default=1.0, type='float',
                help='threshold (in seconds) for logging slow segments (should be < sloweventthreshold)')
    daemon.parser.add_option('--metricsinterval', dest='metricReportInterval', default=60, type='int',
                help='Interval for logging Metrology rates')
    daemon.parser.add_option('--logperfasinfo', dest='LOG_PERF_AS_INFO', default=False, action='store_true',
                help='Output perf data at INFO level - otherwise it will log as DEBUG')
    daemon.parser.add_option('--usemetrology', dest='USE_METROLOGY', default=False, action='store_true',
                help='Use Metrology library for tracking processMessage performance')

@adapter(ZenEventD, DaemonCreatedEvent)
def onDaemonCreated(daemon, event):
    """
    Called at the end of zeneventd's constructor.
    """
    register_eventlet()
    if daemon.options.daemon or daemon.options.cycle:
        daemon._workers = ProcessWorkers(daemon.options.workers, exec_worker, "Event worker")

@adapter(ZenEventD, DaemonStartRunEvent)
def onDaemonStartRun(daemon, event):
    """
    Called when the daemon is ready to begin processing. This handler replaces the one
    defined in zeneventd.py, because onDaemonCreated (above) removes it
    """
    from .zeneventdWorkers import EventDEventletWorker
    # Free up unnecessary database resources in parent zeneventd process
    if daemon.options.daemon or daemon.options.cycle:
        daemon.closedb()
        daemon.closeAll()
        daemon._workers.startWorkers()
        reactor.run()
    else:
        worker = EventDEventletWorker()
        worker.run()
