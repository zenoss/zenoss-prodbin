##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Globals
import logging
import os
import time

from Products.ZenUtils.Utils import zenPath


def monkey_patch_rotatingfilehandler():
    try:
        from cloghandler import ConcurrentRotatingFileHandler
        ConcurrentRotatingFileHandler._lockdir_path = zenPath('var')
        logging.handlers.RotatingFileHandler = ConcurrentRotatingFileHandler
    except ImportError:
        from warnings import warn
        warn("ConcurrentLogHandler package not installed. Using RotatingFileLogHandler. While everything will \
              still work fine, there is a potential for log files overlapping each other.")

monkey_patch_rotatingfilehandler()

from twisted.internet import reactor
from twisted.internet import defer
from datetime import datetime, timedelta
from zope.component import getUtility, adapter
from zope.interface import implements
from zope.component.event import objectEventNotify

from Products.ZenCollector.utils.maintenance import MaintenanceCycle, maintenanceBuildOptions, QueueHeartbeatSender
from Products.ZenCollector.utils.workers import workersBuildOptions
from Products.ZenMessaging.queuemessaging.interfaces import IQueueConsumerTask
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.guid import guid
from zenoss.protocols.interfaces import IAMQPConnectionInfo, IQueueSchema
from zenoss.protocols.protobufs.zep_pb2 import ZepRawEvent, Event, STATUS_DROPPED
from zenoss.protocols.jsonformat import from_dict, to_dict
from zenoss.protocols import hydrateQueueMessage
from Products.ZenMessaging.queuemessaging.QueueConsumer import QueueConsumer
from Products.ZenEvents.events2.processing import (Manager, EventPluginPipe, CheckInputPipe, IdentifierPipe,
    AddDeviceContextAndTagsPipe, TransformAndReidentPipe, TransformPipe, UpdateDeviceContextAndTagsPipe,
    AssignDefaultEventClassAndTagPipe, FingerprintPipe, SerializeContextPipe, ClearClassRefreshPipe,
    EventContext, DropEvent, ProcessingException, CheckHeartBeatPipe)
from Products.ZenEvents.interfaces import IPreEventPlugin, IPostEventPlugin
from Products.ZenEvents.daemonlifecycle import DaemonCreatedEvent, SigTermEvent, SigUsr1Event
from Products.ZenEvents.daemonlifecycle import DaemonStartRunEvent, BuildOptionsEvent

log = logging.getLogger("zen.eventd")

EXCHANGE_ZEP_ZEN_EVENTS = '$ZepZenEvents'
QUEUE_RAW_ZEN_EVENTS = '$RawZenEvents'


class _Measure(object):
    """
    """

    def __init__(self, write):
        self._write = write

    def __enter__(self):
        self.begin = time.time()

    def __exit__(self, *exc_info):
        # propagate the execption if any value in exc_info is not falsey
        # by returning False
        if any(exc_info):
            return False
        duration = time.time() - self.begin
        self._write(duration)


class _Measurements(object):
    """Use to track the runtimes of the event pipes.
    """

    def __init__(self):
        self.times = {}

    @property
    def total(self):
        return sum(self.times.itervalues())

    def measure(self, name):
        return _Measure(lambda d: self._saveMeasure(name, d))

    def _saveMeasure(self, name, duration):
        self.times[name] = duration


class EventPipelineProcessor(object):

    def __init__(self, dmd):
        self.dmd = dmd
        self._manager = Manager(self.dmd, self.logPerfAsInfo, self.slowSegmentThreshold)
        self._pipes = (
            EventPluginPipe(self._manager, IPreEventPlugin, 'PreEventPluginPipe'),
            CheckInputPipe(self._manager),
            IdentifierPipe(self._manager),
            AddDeviceContextAndTagsPipe(self._manager),
            TransformAndReidentPipe(self._manager,
                TransformPipe(self._manager),
                [
                UpdateDeviceContextAndTagsPipe(self._manager),
                IdentifierPipe(self._manager),
                AddDeviceContextAndTagsPipe(self._manager),
                ]),
            AssignDefaultEventClassAndTagPipe(self._manager),
            FingerprintPipe(self._manager),
            SerializeContextPipe(self._manager),
            EventPluginPipe(self._manager, IPostEventPlugin, 'PostEventPluginPipe'),
            ClearClassRefreshPipe(self._manager),
            CheckHeartBeatPipe(self._manager)
        )

        if not self.SYNC_EVERY_EVENT:
            # don't call sync() more often than 1 every 0.5 sec - helps throughput
            # when receiving events in bursts
            self.nextSync = datetime.now()
            self.syncInterval = timedelta(0, 0, 500000)

        if self.useMetrology:
            from metrology import Metrology
            from metrology.reporter.logger import LoggerReporter
            self._messageMeter = Metrology.meter("events-processed")
            if self.logPerfAsInfo:
                self._meterLogger = LoggerReporter(
                    logger=log, level=logging.INFO,
                    interval=self.metricReportInterval,
                    prefix=str("[pid %s] " % os.getpid())
                )
            else:
                self._meterLogger = LoggerReporter(
                    logger=log, level=logging.DEBUG,
                    interval=self.metricReportInterval,
                    prefix=str("[pid %s] " % os.getpid())
                )
            self._meterLogger.start()

    def processMessage(self, message):
        """
        Handles a queue message, can call "acknowledge" on the Queue Consumer
        class when it is done with the message
        """

        if self.useMetrology:
            self._messageMeter.mark()

        pid = os.getpid()

        other_measure = _Measurements()
        pipe_measure = _Measurements()

        with other_measure.measure("overall"):
            with other_measure.measure("sync"):
                if self.SYNC_EVERY_EVENT:
                    doSync = True
                else:
                    # sync() db if it has been longer than
                    # self.syncInterval since the last time
                    currentTime = datetime.now()
                    doSync = currentTime > self.nextSync
                    self.nextSync = currentTime + self.syncInterval

                if doSync:
                    self.dmd._p_jar.sync()

            try:
                retry = True
                processed = False
                while not processed:
                    try:
                        # extract event from message body
                        zepevent = ZepRawEvent()
                        zepevent.event.CopyFrom(message)
                        if log.isEnabledFor(logging.DEBUG):
                            log.debug("[pid %s] Received event: %s",  pid, to_dict(zepevent.event))

                        eventContext = EventContext(log, zepevent)

                        with other_measure.measure("pipes"):
                            for pipe in self._pipes:
                                with pipe_measure.measure(pipe.name):
                                    eventContext = pipe(eventContext)
                                if log.isEnabledFor(logging.DEBUG):
                                    log.debug(
                                        "[pid %s] After pipe %s, event context is %s",
                                        pid, pipe.name, to_dict(eventContext.zepRawEvent)
                                    )
                                if eventContext.event.status == STATUS_DROPPED:
                                    raise DropEvent('Dropped by %s' % pipe, eventContext.event)

                        processed = True

                    except AttributeError:
                        # _manager throws Attribute errors if connection to zope is lost - reset and retry ONE time
                        if retry:
                            retry = False
                            log.debug("[pid %s] Resetting connection to catalogs", pid)
                            self._manager.reset()
                        else:
                            raise

            except DropEvent:
                # we want these to propagate out
                raise
            except Exception as e:
                log.info("[pid %s] Failed to process event, forward original raw event: %s",
                         pid, to_dict(zepevent.event))
                # Pipes and plugins may raise ProcessingException's for their own reasons - only log unexpected
                # exceptions of other type (will insert stack trace in log)
                if not isinstance(e, ProcessingException):
                    log.exception(e)

                # construct wrapper event to report event processing failure (including content of the # original event)
                origzepevent = ZepRawEvent()
                origzepevent.event.CopyFrom(message)
                failReportEvent = dict(
                    uuid=guid.generate(),
                    created_time=int(time.time()*1000),
                    fingerprint='|'.join(['zeneventd', 'processMessage', repr(e)]),
                    # Don't send the *same* event class or we trash and and crash endlessly
                    eventClass='/',
                    summary='Internal exception processing event: %r' % e,
                    message='Internal exception processing event: %r/%s' % (e, to_dict(origzepevent.event)),
                    severity=4,
                )
                zepevent = ZepRawEvent()
                zepevent.event.CopyFrom(from_dict(Event, failReportEvent))
                eventContext = EventContext(log, zepevent)
                eventContext.eventProxy.device = 'zeneventd'
                eventContext.eventProxy.component = 'processMessage'

            if log.isEnabledFor(logging.DEBUG):
                log.debug("[pid %s] Publishing event: %s", pid, to_dict(eventContext.zepRawEvent))

        self._reportMeasurements(
            pid, other_measure, pipe_measure, to_dict(zepevent.event).get('uuid'), to_dict(zepevent.event).get('summary')
        )
        return eventContext.zepRawEvent

    def _reportMeasurements(self, pid, other_measure, pipe_measure, uuid, summary):
        overall_time = other_measure.times["overall"]
        if overall_time > self.slowEventThreshold:
            durations = {
                "pipes": other_measure.times["pipes"],
                "processing_minus_pipes":
                    overall_time - other_measure.times["sync"] - other_measure.times["pipes"],
                "sync": other_measure.times["sync"]
            }
            # Build a list of the slow segments
            slow_durations = []
            for key, duration in durations.iteritems():
                if duration > self.slowSegmentThreshold:
                    slow_durations.append("%s took %.2fs" % (key, duration))
            # Build a list of the slow pipes
            slow_pipes = []
            for key, duration in pipe_measure.times.iteritems():
                if duration > self.slowSegmentThreshold:
                    slow_pipes.append("%s took %.2fs" % (key, duration))

            # Build the perf_message string combining all wanted elements
            perf_message = (
                "[pid %s] processMessage() took %.2fs (exceeded %.1fs threshold)"
                "  ##  Event uuid '%s'  ##  Event summary '%s'"
            ) % (
                pid, overall_time, self.slowEventThreshold, uuid, summary
            )
            if slow_durations:
                perf_message += "  ##  Slow segments: %s" % ', '.join(slow_durations)
            if slow_pipes:
                perf_message += "  ##  Slow pipes: %s" % ', '.join(slow_pipes)
            perf_message += "  ##"

            if self.logPerfAsInfo:
                log.info(perf_message)
            else:
                log.debug(perf_message)


class BaseQueueConsumerTask(object):

    implements(IQueueConsumerTask)

    def __init__(self, processor):
        self.processor = processor
        self._queueSchema = getUtility(IQueueSchema)
        self.dest_routing_key_prefix = 'zenoss.zeneventd'
        self._dest_exchange = self._queueSchema.getExchange(EXCHANGE_ZEP_ZEN_EVENTS)

    def _routing_key(self, event):
        return (self.dest_routing_key_prefix +
                event.event.event_class.replace('/', '.').lower())


class TwistedQueueConsumerTask(BaseQueueConsumerTask):

    def __init__(self, processor):
        BaseQueueConsumerTask.__init__(self, processor)
        self.queue = self._queueSchema.getQueue(QUEUE_RAW_ZEN_EVENTS)

    @defer.inlineCallbacks
    def processMessage(self, message):
        try:
            hydrated = hydrateQueueMessage(message, self._queueSchema)
        except Exception as e:
            log.error("Failed to hydrate raw event: %s", e)
            yield self.queueConsumer.acknowledge(message)
        else:
            try:
                zepRawEvent = self.processor.processMessage(hydrated)
                if log.isEnabledFor(logging.DEBUG):
                    log.debug("Publishing event: %s", to_dict(zepRawEvent))
                yield self.queueConsumer.publishMessage(EXCHANGE_ZEP_ZEN_EVENTS,
                    self._routing_key(zepRawEvent), zepRawEvent, declareExchange=False)
                yield self.queueConsumer.acknowledge(message)
            except DropEvent as e:
                if log.isEnabledFor(logging.DEBUG):
                    log.debug('%s - %s' % (e.message, to_dict(e.event)))
                yield self.queueConsumer.acknowledge(message)
            except ProcessingException as e:
                log.error('%s - %s' % (e.message, to_dict(e.event)))
                log.exception(e)
                yield self.queueConsumer.reject(message)
            except Exception as e:
                log.exception(e)
                yield self.queueConsumer.reject(message)


class EventDTwistedWorker(object):
    def __init__(self, dmd):
        super(EventDTwistedWorker, self).__init__()
        self._amqpConnectionInfo = getUtility(IAMQPConnectionInfo)
        self._queueSchema = getUtility(IQueueSchema)
        self._consumer_task = TwistedQueueConsumerTask(EventPipelineProcessor(dmd))
        self._consumer = QueueConsumer(self._consumer_task, dmd)

    def run(self):
        reactor.callWhenRunning(self._start)
        reactor.run()

    def _start(self):
        reactor.addSystemEventTrigger('before', 'shutdown', self._shutdown)
        self._consumer.run()

    @defer.inlineCallbacks
    def _shutdown(self):
        if self._consumer:
            yield self._consumer.shutdown()


class ZenEventD(ZCmdBase):

    def __init__(self, *args, **kwargs):
        super(ZenEventD, self).__init__(*args, **kwargs)
        EventPipelineProcessor.SYNC_EVERY_EVENT = self.options.SYNC_EVERY_EVENT
        EventPipelineProcessor.logPerfAsInfo = self.options.logPerfAsInfo
        EventPipelineProcessor.useMetrology = self.options.useMetrology
        EventPipelineProcessor.metricReportInterval = self.options.metricReportInterval
        EventPipelineProcessor.slowEventThreshold = self.options.slowEventThreshold
        EventPipelineProcessor.slowSegmentThreshold = self.options.slowSegmentThreshold
        self._heartbeatSender = QueueHeartbeatSender('localhost',
                                                     'zeneventd',
                                                     self.options.maintenancecycle * 3)
        self._maintenanceCycle = MaintenanceCycle(self.options.maintenancecycle,
                                  self._heartbeatSender)
        objectEventNotify(DaemonCreatedEvent(self))

    def sigTerm(self, signum=None, frame=None):
        log.info("Shutting down...")
        self._maintenanceCycle.stop()
        objectEventNotify(SigTermEvent(self))
        super(ZenEventD, self).sigTerm(signum, frame)

    def run(self):
        if self.options.daemon or self.options.cycle:
            self._maintenanceCycle.start()
        objectEventNotify(DaemonStartRunEvent(self))

    def sighandler_USR1(self, signum, frame):
        super(ZenEventD, self).sighandler_USR1(signum, frame)
        log.debug('sighandler_USR1 called %s' % signum)
        objectEventNotify(SigUsr1Event(self, signum))

    def buildOptions(self):
        # ZEN-15338: Move parser options into zeneventdEvents.py
        #  * Add all future parser options to zeneventdEvents.py
        super(ZenEventD, self).buildOptions()
        objectEventNotify(BuildOptionsEvent(self))


class onDaemonStartRun(object):
    pass

if __name__ == '__main__':
    # explicit import of ZenEventD to activate enterprise extensions
    from Products.ZenEvents.zeneventd import ZenEventD
    zed = ZenEventD()
    zed.run()
