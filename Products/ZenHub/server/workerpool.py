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
import logging

from twisted.internet import defer
from twisted.spread import pb
from zope.component import adapter, provideHandler

from Products.ZenHub.errors import RemoteException

from .events import ReportWorkerStatus
from .utils import getLogger


class WorkerPool(
    collections.Container, collections.Iterable, collections.Sized
):
    """Pool of ZenHubWorker RemoteReference objects."""

    def __init__(self, name):
        """Initialize a WorkerPool instance.

        ZenHubWorker will specify a "queue" to accept tasks from.  The
        name of the queue is given by the 'name' parameter.

        :param str name: Name of the "queue" associated with this pool.
        """
        # __available contains workers (by ID) available for work
        self.__available = WorkerAvailabilityQueue()
        self.__workers = {}  # Worker refs by worker.sessionId
        self.__services = {}  # Service refs by worker.sessionId
        self.__name = name
        self.__log = getLogger(self)
        # Declare a handler for ReportWorkerStatus events
        provideHandler(self.handleReportStatus)

    @property
    def name(self):
        return self.__name

    def add(self, worker):
        """Add a worker to the pool.

        Note: the worker is expected to have both 'workerId' and
        'sessionId' attributes.

        @param worker {RemoteReference} A reference to the remote worker
        """
        assert not isinstance(
            worker, WorkerRef
        ), "worker may not be a WorkerRef"
        sessionId = worker.sessionId
        if sessionId in self.__workers:
            self.__log.debug(
                "Worker already registered worker=%s", worker.workerId
            )
            return
        self.__workers[sessionId] = worker
        self.__services[sessionId] = RemoteServiceRegistry(worker)
        self.__available.add(sessionId)
        self.__log.debug(
            "Worker registered worker=%s total-workers=%s",
            worker.workerId,
            len(self.__workers),
        )

    def remove(self, worker):
        """Remove a worker from the pool.

        Note: the worker is expected to have both 'workerId' and
        'sessionId' attributes.

        @param worker {RemoteReference} A reference to the remote worker
        """
        assert not isinstance(
            worker, WorkerRef
        ), "worker may not be a WorkerRef"
        sessionId = worker.sessionId
        self.__remove(sessionId, worker=worker)

    def __remove(self, sessionId, worker=None):
        if sessionId not in self.__workers:
            self.__log.debug(
                "Worker not registered worker=%s", worker.workerId
            )
            return
        if worker is None:
            worker = self.__workers[sessionId]
        del self.__workers[sessionId]
        del self.__services[sessionId]
        self.__available.discard(sessionId)
        self.__log.debug(
            "Worker unregistered worker=%s total-workers=%s",
            worker.workerId,
            len(self.__workers),
        )

    def __contains__(self, worker):
        """Return True if worker is registered, else False is returned.

        Note: the worker is expected to have a 'sessionId' attribute.

        @param worker {RemoteReference} A reference to the remote worker
        """
        return self.__workers.get(worker.sessionId) is worker

    def __len__(self):
        return len(self.__workers)

    def __iter__(self):
        return (
            self.__makeref(worker)
            for worker in self.__workers.itervalues()
            if worker is not None
        )

    @adapter(ReportWorkerStatus)
    def handleReportStatus(self, event):
        """Instructs workers to report their status.

        Returns a DeferredList that fires when all the workers have
        completed reporting their status.
        """
        deferreds = []
        for worker in self.__workers.viewvalues():
            dfr = worker.callRemote("reportStatus")
            dfr.addErrback(
                lambda ex: self.__log.error(
                    "Failed to report status (%s): %s", worker.workerId, ex
                ),
            )
            deferreds.append(dfr)
        return defer.DeferredList(deferreds)

    @property
    def available(self):
        """Return the number of workers available for work."""
        return len(self.__available)

    @defer.inlineCallbacks
    def hire(self):
        """Return a valid worker.

        This method blocks until a worker is available.
        """
        while True:
            sessionId = yield self.__available.pop()
            try:
                worker = self.__workers[sessionId]
                # Ping the worker to test whether it still exists
                yield worker.callRemote("ping")
            except (pb.PBConnectionLost, pb.DeadReferenceError) as ex:
                msg = _bad_worker_messages.get(type(ex))
                self.__log.error(msg, worker.workerId)
                self.__remove(sessionId, worker=worker)
            except Exception:
                self.__log.exception("Unexpected error")
                self.__remove(sessionId)
            else:
                self.__log.debug("Worker hired worker=%s", worker.workerId)
                defer.returnValue(self.__makeref(worker))

    def layoff(self, workerref):
        """Make the worker available for hire."""
        worker = workerref.ref
        # Verify the worker is the same instance before making it
        # available for hire again.
        worker_p = self.__workers.get(worker.sessionId)
        if worker_p:
            self.__log.debug("Worker layed off worker=%s", worker.workerId)
            self.__available.add(worker.sessionId)
        else:
            self.__log.debug("Worker retired worker=%s", worker.workerId)

    def __makeref(self, worker):
        return WorkerRef(worker, self.__services[worker.sessionId])


_bad_worker_messages = {
    pb.PBConnectionLost: "Worker failed ping test worker=%s",
    pb.DeadReferenceError: (
        "Worker no longer available (dead reference) worker=%s"
    ),
}


class RemoteServiceRegistry(object):
    """Registry of RemoteReferences to services in zenhubworker."""

    def __init__(self, worker):
        """Initialize a RemoteServiceRegistry instance.

        :param worker: The ZenHubWorker reference
        :type worker: pb.RemoteReference
        """
        self.__services = {}  # (service-name, monitor): service-ref
        self.__worker = worker

    def get(self, key, default=None):
        return self.__services.get(key, default)

    def __contains__(self, key):
        return key in self.__services

    @defer.inlineCallbacks
    def lookup(self, service, monitor):
        """Retrieve a service reference asynchronously."""
        remoteRef = self.__services.get((service, monitor))
        if remoteRef is None:
            remoteRef = yield self.__worker.callRemote(
                "getService", service, monitor
            )
            self.__services[(service, monitor)] = remoteRef
        defer.returnValue(remoteRef)


class WorkerRef(object):
    """Wrapper around zenhubworker RemoteReference objects.

    Used to simplify access to the services associated with a worker.
    """

    def __init__(self, worker, services):
        """ """
        self.__worker = worker
        self.__services = services
        self.__log = getLogger(self)

    @property
    def ref(self):
        return self.__worker

    @property
    def services(self):
        return self.__services

    def __getattr__(self, name):
        return getattr(self.__worker, name)

    @defer.inlineCallbacks
    def run(self, call):
        """Execute the call.

        @param job {ServiceCall} Details on the RPC method to invoke.
        @raises Exception if an error occurs while attempting to
            execute a remote procedure call.  An RPC error may occur while
            retrieving the remote service reference or when invoking the
            job specified method on the remote service reference.
        """
        try:
            service = yield self.__services.lookup(call.service, call.monitor)
            self.__log.debug(
                "Retrieved remote service service=%s id=%s worker=%s",
                call.service,
                call.id,
                self.__worker.workerId,
            )
        except Exception as ex:
            if self.__log.isEnabledFor(logging.DEBUG):
                self.__log.error(
                    "Failed to retrieve remote service "
                    "service=%s worker=%s error=(%s) %s",
                    call.service,
                    self.__worker.workerId,
                    ex.__class__.__name__,
                    ex,
                )
            raise

        try:
            result = yield service.callRemote(
                call.method, *call.args, **call.kwargs
            )
            self.__log.debug(
                "Executed remote method service=%s method=%s id=%s worker=%s",
                call.service,
                call.method,
                call.id.hex,
                self.__worker.workerId,
            )
            defer.returnValue(result)
        except (RemoteException, pb.RemoteError) as ex:
            if self.__log.isEnabledFor(logging.DEBUG):
                self.__log.error(
                    "Remote method failed "
                    "service=%s method=%s id=%s worker=%s error=%s",
                    call.service,
                    call.method,
                    call.id.hex,
                    self.__worker.workerId,
                    ex,
                )
            raise
        except Exception as ex:
            if self.__log.isEnabledFor(logging.DEBUG):
                self.__log.error(
                    "Failed to execute remote method "
                    "service=%s method=%s id=%s worker=%s error=(%s) %s",
                    call.service,
                    call.method,
                    call.id.hex,
                    self.__worker.workerId,
                    ex.__class__.__name__,
                    ex,
                )
            raise


class WorkerAvailabilityQueue(defer.DeferredQueue):
    """Extends defer.DeferredQueue with more set-like behavior."""

    def __len__(self):
        return len(self.pending)

    # Alias pop to get -- DeferredQueue.get removes the value from the queue.
    pop = defer.DeferredQueue.get

    def add(self, item):
        if item not in self.pending:
            self.put(item)

    def discard(self, item):
        if item in self.pending:
            self.pending.remove(item)
