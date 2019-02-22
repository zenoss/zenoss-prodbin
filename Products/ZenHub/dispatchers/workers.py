##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import collections
import time

from contextlib import contextmanager

from twisted.internet import defer
from twisted.spread import pb
from zope.interface import implementer

from Products.ZenUtils.logger import getLogger
from Products.ZenHub.PBDaemon import RemoteException

from .base import IAsyncDispatch
from .workerpool import ServiceCallError


@implementer(IAsyncDispatch)
class WorkerPoolDispatcher(object):
    """An executor that executes service/method calls on remote workers.

    The WorkerPoolDispatcher serves as the 'default' dispatcher for the
    DispatchingExecutor executor.
    """

    # No routes needed for default dispatcher
    routes = ()

    def __init__(self, reactor, worklist, pool, stats):
        """Initializes a WorkerPoolDispatcher instance.
        """
        self.__reactor = reactor
        self.__worklist = worklist
        self.__workers = pool
        self.__stats = stats
        self.__executeListeners = []
        self.__log = getLogger("zenhub", self)

    def onExecute(self, listener):
        """Register a listener that will be called prior the execution of
        a job on a worker.

        @param listener {callable}
        """
        self.__executeListeners.append(listener)

    def reportWorkerStatus(self):
        """Instructs workers to report their status.

        Returns a DeferredList that fires when all the workers have
        completed reporting their status.
        """
        deferreds = []
        for worker in self.__workers:
            dfr = worker.callRemote("reportStatus")
            dfr.addErrback(
                lambda ex: self.__log.error(
                    "Failed to report status (%s): %s",
                    worker.workerId, ex
                )
            )
            deferreds.append(dfr)
        return defer.DeferredList(deferreds)

    def submit(self, job):
        """Submits a job for execution.

        Returns a deferred that will fire when execution completes.
        """
        ajob = AsyncServiceCallJob(job)
        self.__worklist.push(ajob)
        # Schedule a call to _execute to process this newly submitted job.
        self.__reactor.callLater(0, self._execute)
        self.__log.info(
            "Job submitted: (%s) %s.%s", job.monitor, job.service, job.method
        )
        return ajob.deferred

    @defer.inlineCallbacks
    def _execute(self):
        """Executes the next job in the worklist.
        """
        # Ensure that 'asyncjob' exists for use in exception handler.
        asyncjob = None
        try:
            # An empty worklist means nothing to do.
            # No need to schedule a call to _execute if there are no jobs.
            if not self.__worklist:
                defer.returnValue(None)

            # No workers available means wait and try again
            if not self.__workers.available:
                self.__reactor.callLater(0.1, self._execute)
                defer.returnValue(None)

            self.__log.info(
                "There are %s workers available", self.__workers.available
            )
            self.__log.info("Worklist has %s jobs", len(self.__worklist))
            asyncjob = self.__worklist.pop()

            # Notify listeners before executing the job.
            yield defer.DeferredList([
                self._call_listener(listener, asyncjob.job)
                for listener in self.__executeListeners
            ])

            yield self._call_service(asyncjob)
        except Exception:
            self.__log.exception("Unexpected failure")
            if asyncjob is not None:
                self.__worklist.pushfront(asyncjob)

        # If worklist contains a job, schedule another call to _execute.
        # However, introduce a 0.1 second delay to avoid maximizing CPU
        # utilization testing for a lack of available workers or logging
        # a recuring error with a job.
        if self.__worklist:
            self.__reactor.callLater(0.1, self._execute)

    def _call_listener(self, listener, job):
        """Returns a Deferred object that wraps the 'listener' invocation
        in a Deferred object and installs an error handler to handle
        exceptions raised by the listener.
        """
        dfr = defer.maybeDeferred(listener, job)
        dfr.addErrback(
            lambda x: self.__log.error(
                "Error in listener %r: %s", listener, x
            )
        )
        return dfr

    @defer.inlineCallbacks
    def _call_service(self, asyncjob):
        job = asyncjob.job
        with self.__workers.borrow() as worker, \
                self.__stats.monitor(worker, asyncjob):
            try:
                result = yield worker.run(job)
            except (RemoteException, pb.RemoteError) as ex:
                self.__reactor.callLater(0, asyncjob.failure, ex)
            except ServiceCallError as ex:
                if worker in self.__workers:
                    self.__log.exception(
                        "(worker %s) %s", worker.workerId, ex
                    )
                    self.__reactor.callLater(
                        0, asyncjob.failure,
                        pb.Error("Internal ZenHub error: %s" % (ex,))
                    )
                else:
                    self.__log.error(
                        "(worker %s) Bad worker ref: %s", worker.workerId, ex
                    )
                    # Bad worker reference, so retry the call
                    self.__worklist.pushfront(asyncjob)
            else:
                self.__reactor.callLater(0, asyncjob.success, result)


class StatsMonitor(object):

    def __init__(self):
        self.__worker_stats = {}
        self.__job_stats = {}
        self.__log = getLogger("zenhub", WorkerPoolDispatcher)

    @property
    def workers(self):
        return self.__worker_stats

    @property
    def jobs(self):
        return self.__job_stats

    @contextmanager
    def monitor(self, worker, asyncjob):
        """
        """
        job = asyncjob.job
        wid = worker.workerId
        jobDesc = "%s:%s.%s" % (job.monitor, job.service, job.method)

        start = time.time()

        ws = self.__worker_stats.get(wid, None)
        if ws is None:
            ws = WorkerStats()
            self.__worker_stats[wid] = ws
            ws.description = jobDesc
            ws.lastupdate = start

        js = self.__job_stats.get(job.method, None)
        if js is None:
            js = JobStats()
            self.__job_stats[job.method] = js
            js.last_called_time = start

        ws.status = "Busy"
        ws.previdle = start - ws.lastupdate
        ws.lastupdate = start

        js.count += 1
        js.idle_total += start - js.last_called_time
        js.last_called_time = start

        self.__log.info("(worker %s) Begin work job=%s", wid, jobDesc)

        yield self

        finish = time.time()
        elapsed = finish - start

        js.last_called_time = finish
        js.running_total += elapsed

        ws.lastupdate = finish
        ws.status = "Idle"

        self.__log.info(
            "(worker %s) Finished work job=%s elapsed=%0.3f",
            wid, jobDesc, elapsed
        )
        lifetime = finish - asyncjob.recvtime
        self.__log.info(
            "Job %s.%s (%s) lifetime was %0.3f seconds",
            job.service, job.method, job.monitor, lifetime
        )


class WorkerStats(object):

    __slots__ = ("status", "description", "lastupdate", "previdle")

    def __init__(self):
        self.status = ""
        self.description = ""
        self.lastupdate = 0
        self.previdle = 0


class JobStats(object):

    __slots__ = ("count", "idle_total", "running_total", "last_called_time")

    def __init__(self):
        self.count = 0
        self.idle_total = 0.0
        self.running_total = 0.0
        self.last_called_time = 0


ServiceCallJob = collections.namedtuple(
    "ServiceCallJob", "service monitor method args kwargs"
)


class AsyncServiceCallJob(object):
    """Wraps a ServiceCallJob object to track for use with
    WorkerPoolDispatcher.
    """

    def __init__(self, job):
        self.job = job
        self.method = job.method
        self.deferred = defer.Deferred()
        self.recvtime = time.time()

    def failure(self, error):
        self.deferred.errback(error)

    def success(self, result):
        self.deferred.callback(result)
