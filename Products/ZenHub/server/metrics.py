##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

# from contextlib import contextmanager

import time

from collections import defaultdict, Counter
from datetime import datetime, timedelta
from metrology import Metrology
from metrology.registry import registry
from metrology.instruments import Gauge

from Products.ZenUtils.Logger import getLogger

from .priority import ServiceCallPriority


class PriorityListLengthGauge(Gauge):
    """Metrology gauge for priority queues."""

    def __init__(self, worklist, priority):
        self.__worklist = worklist
        self.__priority = priority

    @property
    def value(self):
        return self.__worklist.length_of(self.__priority)


class WorklistLengthGauge(Gauge):
    """Metrology gauge over all the queues."""

    def __init__(self, worklist):
        self.__worklist = worklist

    @property
    def value(self):
        return len(self.__worklist)


_gauge_priority_map = {
    "zenhub.eventWorkList": ServiceCallPriority.EVENTS,
    "zenhub.admWorkList": ServiceCallPriority.MODELING,
    "zenhub.otherWorkList": ServiceCallPriority.OTHER,
    "zenhub.singleADMWorkList": ServiceCallPriority.SINGLE_MODELING,
}
_metricname_worklist = "zenhub.workList"


def register_metrics_on_worklist(worklist):
    metricNames = {x[0] for x in registry}

    for metricName, priority in _gauge_priority_map.iteritems():
        if metricName not in metricNames:
            gauge = PriorityListLengthGauge(worklist, priority)
            Metrology.gauge(metricName, gauge)

    # Original metric name
    if _metricname_worklist not in metricNames:
        gauge = WorklistLengthGauge(worklist)
        Metrology.gauge(_metricname_worklist, gauge)


def _get_worklist_metrics():
    instruments = dict(registry)

    gauges = {
        priority: instruments[metricName].value
        for metricName, priority in _gauge_priority_map.items()
        if metricName in instruments
    }
    if _metricname_worklist in instruments:
        gauges["total"] = instruments[_metricname_worklist].value
    return gauges


def make_status_reporter():
    monitor = StatsMonitor()
    return ZenHubStatusReporter(monitor)


class ZenHubStatusReporter(object):
    """Status Reporter for ZenHub."""

    def __init__(self, stats):
        """Initialize an instance of ZenHubStatusReporter.

        :param stats: Worker and Task statistics tracker.
        :type stats: StatsMonitor
        """
        self.__stats = stats
        self.__heading_priority_seq = (
            ("Events", ServiceCallPriority.EVENTS),
            ("Other", ServiceCallPriority.OTHER),
            ("ApplyDataMaps (batch)", ServiceCallPriority.MODELING),
            ("ApplyDataMaps (single)", ServiceCallPriority.SINGLE_MODELING),
        )

    def getReport(self):
        """Return a report on the services."""
        now = time.time()

        worklist_metrics = _get_worklist_metrics()
        lines = ["Worklist Stats:"]
        lines.extend(
            "   {:<22}: {}".format(priority, worklist_metrics[key])
            for priority, key in self._heading_priority_seq
        )
        lines.extend([
            "   {:<22}: {}".format("Total", worklist_metrics["total"]),
            "",
            "Service Call Statistics:",
            "   {:<32} {:>8} {:>12}  {}".format(
                "method", "count",
                "running_total", "last_called_time",
            ),
        ])

        tasks = self.__stats.tasks
        statline = " - {:<32} {:>8} {:>12}  {:%Y-%m-%d %H:%M:%S}"
        sorted_by_running_total = sorted(
            tasks.iteritems(), key=lambda e: -(e[1].running_total),
        )
        lines.extend(
            statline.format(
                method, stats.count,
                timedelta(seconds=round(stats.running_total)),
                datetime.fromtimestamp(stats.last_completed),
            )
            for method, stats in sorted_by_running_total
        )

        workers = self.__stats.workers
        lines.extend([
            "",
            "Worker Statistics:",
        ])
        nostatsFmt = "    {:>2}:Idle [] No tasks run"
        statsFmt = "    {:>2}:{} [{}  elapsed: {}] idle: {}"
        for workerId, stats in sorted(workers.iteritems()):
            if not stats or not (stats.current_task or stats.last_task):
                lines.append(nostatsFmt.format(workerId))
                continue
            if stats.current_task:
                ct = stats.current_task
                lt = stats.last_task
                desc = ct.description
                elapsed = timedelta(seconds=round(now - ct.started))
                if lt:
                    idle = timedelta(seconds=round(ct.started - lt.completed))
                else:
                    idle = "n/a"
            else:
                lt = stats.last_task
                desc = lt.description
                elapsed = timedelta(seconds=round(lt.completed - lt.started))
                idle = timedelta(seconds=round(now - lt.completed))
            lines.append(statsFmt.format(
                workerId, stats.status, desc, elapsed, idle,
            ))
        return '\n'.join(lines)


class StatsMonitor(object):
    """Records statistics on zenhubworker activity."""

    def __init__(self):
        self.__counters = Counter()
        self.__worker_stats = defaultdict(_WorkerStats)
        self.__task_stats = defaultdict(_TaskStats)
        self.__log = getLogger("zenhub", self)

    @property
    def counters(self):
        return self.__counters

    @property
    def workers(self):
        return self.__worker_stats

    @property
    def tasks(self):
        return self.__task_stats

    def update_rrd_stats(self, rrdstats, service_manager):
        totalTime = sum(
            s.callTime for s in service_manager.services.values()
        )
        rrdstats.gauge('services', len(service_manager.services))
        rrdstats.counter('totalCallTime', totalTime)

        instruments = dict(registry)
        if _metricname_worklist in instruments:
            rrdstats.gauge(
                'workListLength',
                instruments[_metricname_worklist].value,
            )

        for name, value in self.__counters.items():
            rrdstats.counter(name, value)

    def handleReceived(self):
        self.__counters["workerItems"] += 1

    def handleStarted(self, workerId, call):
        """Update stats from the call."""
        now = time.time()
        ws = self.__worker_stats[workerId]
        ts = self.__task_stats[call.method]

        ws.status = "Busy"
        if ws.last_task_completed:
            ws.idle += now - ws.last_task.completed

        ws.current_task = _TaskInfo()
        ws.current_task.description = "%s.%s" % (call.service, call.method)
        ws.current_task.started = now
        ts.count += 1

    def handleCompleted(self, workerId, call):
        """Update stats from the ServiceCallCompleted event."""
        now = time.time()
        ws = self.__worker_stats[workerId]
        ts = self.__task_stats[call.method]

        ts.last_completed = now
        ts.running_total += now - ws.current_task.started

        ws.last_task = ws.current_task
        ws.last_task.completed = now
        ws.current_task = None
        ws.status = "Idle"


class _TaskInfo(object):
    """Stats on a worker's current task."""

    __slots__ = ("description", "started", "completed")

    def __init__(self):
        self.description = ""
        self.started = None
        self.completed = None


class _WorkerStats(object):
    """Status of particular zenhubworker."""

    __slots__ = ("status", "current_task", "last_task", "idle")

    def __init__(self):
        self.status = ""
        self.current_task = None
        self.last_task = None
        self.idle = 0.0


class _TaskStats(object):
    """Status of a particular service call."""

    __slots__ = ("count", "running_total", "last_completed")

    def __init__(self):
        self.count = 0
        self.running_total = 0.0
        self.last_completed = 0.0
