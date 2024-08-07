##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging

from collections import Container, Iterable, Sized

from twisted.internet import defer
from twisted.spread import pb
from zope.component import adapter, provideHandler

from Products.ZenHub.errors import RemoteException

from .events import ReportWorkerStatus
from .utils import getLogger


class WorkerPool(Container, Iterable, Sized):
    """Pool of ZenHubWorker RemoteReference objects."""

    def __init__(self, name):
        """Initialize a WorkerPool instance.

        ZenHubWorker will specify a "worklist" to accept tasks from.  The
        name of the worklist is given by the 'name' parameter.

        :param str name: Name of the "worklist" associated with this pool.
        """
        # __available contains workers (by ID) available for work
        self.__available = WorkerAvailabilityQueue()

        # Worker refs by worker.name
        # type: {str: RemoteReference}
        self.__workers = {}

        # Service refs by worker.name
        # type: {str: RemoteServiceRegistry}
        self.__services = {}

        self.__name = name
        self.__log = getLogger(self)
        # Declare a handler for ReportWorkerStatus events
        provideHandler(self.handleReportStatus)

    @property
    def name(self):
        return self.__name

    def add(self, worker):  # type: (worker: RemoteReference) -> None
        """Add a worker to the pool.

        The added worker will replace any existing worker that has the
        same `name` attribute value.

        @type worker: RemoteReference
        """
        if isinstance(worker, WorkerRef):
            raise TypeError("worker may not be a WorkerRef")
        name = worker.name
        replaced = False
        stored_worker = self.__workers.get(name)
        if stored_worker is worker:
            return
        elif stored_worker is not None:
            replaced = True
            self.__discard(name)
        self.__workers[name] = worker
        self.__services[name] = RemoteServiceRegistry(worker)
        self.__available.add(name)
        self.__log.debug(
            "%s worker  worker=%s total-workers=%s",
            "added" if not replaced else "replaced",
            worker.name,
            len(self.__workers),
        )

    def remove(self, worker):
        """Remove a worker from the pool.

        @param worker {RemoteReference} A reference to the remote worker
        """
        if isinstance(worker, WorkerRef):
            raise TypeError("worker may not be a WorkerRef")
        stored_worker = self.__workers.get(worker.name)
        if stored_worker is not worker:
            self.__log.debug(
                "cannot remove unknown worker  worker=%s", worker.name
            )
            return
        self.__discard(worker.name)
        self.__log.debug(
            "removed worker  worker=%s total-workers=%s",
            worker.name,
            len(self.__workers),
        )

    def __discard(self, name):
        del self.__workers[name]
        del self.__services[name]
        self.__available.discard(name)

    def __contains__(self, worker):
        """Return True if worker is present, else False is returned.

        Note: the worker is expected to have a 'name' attribute.

        @param worker {RemoteReference} A reference to the remote worker
        """
        if isinstance(worker, WorkerRef):
            raise TypeError("worker may not be a WorkerRef")
        return self.__workers.get(worker.name) is worker

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
                lambda ex, name=worker.name: self.__log.error(
                    "Failed to report status (%s): %s", name, ex
                ),
            )
            deferreds.append(dfr)
        return defer.DeferredList(deferreds)

    @property
    def available(self):
        """Return the number of workers available for work."""
        return len(self.__available)

    @defer.inlineCallbacks
    def hire(self):  # type: () -> WorkerRef
        """Return a valid worker.

        This method blocks until a worker is available.
        """
        while True:
            name = yield self.__available.pop()
            try:
                worker = self.__workers[name]
                # Ping the worker to test whether it still exists
                yield worker.callRemote("ping")
            except KeyError:
                self.__log.error(
                    "available worker doesn't exist  worker=%s", name
                )
            except (pb.PBConnectionLost, pb.DeadReferenceError) as ex:
                msg = _bad_worker_messages.get(type(ex))
                self.__log.error(msg, worker.name)
                self.__discard(name)
            except Exception:
                self.__log.exception("unexpected error")
                self.__discard(name)
            else:
                self.__log.debug("hired worker  worker=%s", worker.name)
                defer.returnValue(self.__makeref(worker))

    def layoff(self, workerref):  # type: (workerref: WorkerRef) -> None
        """Make the worker available for hire."""
        if not isinstance(workerref, WorkerRef):
            raise TypeError("worker must be a WorkerRef")
        worker = workerref.ref
        if worker.name not in self.__workers:
            self.__log.debug("Worker retired worker=%s", worker.name)
            return
        if worker.name not in self.__available:
            self.__available.add(worker.name)
            self.__log.debug("layed off worker  worker=%s", worker.name)

    def __makeref(self, worker):
        return WorkerRef(worker, self.__services[worker.name])


_bad_worker_messages = {
    pb.PBConnectionLost: "worker failed ping test  worker=%s",
    pb.DeadReferenceError: (
        "worker no longer available (dead reference)  worker=%s"
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
                self.__worker.name,
            )
        except Exception as ex:
            if self.__log.isEnabledFor(logging.DEBUG):
                self.__log.error(
                    "Failed to retrieve remote service "
                    "service=%s worker=%s error=(%s) %s",
                    call.service,
                    self.__worker.name,
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
                self.__worker.name,
            )
            defer.returnValue(result)
        except (RemoteException, pb.RemoteError) as ex:
            if self.__log.isEnabledFor(logging.DEBUG):
                self.__log.error(
                    "Remote method failed  "
                    "service=%s method=%s id=%s worker=%s error=%s",
                    call.service,
                    call.method,
                    call.id.hex,
                    self.__worker.name,
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
                    self.__worker.name,
                    ex.__class__.__name__,
                    ex,
                )
            raise


class WorkerAvailabilityQueue(defer.DeferredQueue):
    """Extends defer.DeferredQueue with more set-like behavior."""

    def __len__(self):
        return len(self.pending)

    def __contains__(self, item):
        return item in self.pending

    # Alias pop to get -- DeferredQueue.get removes the value from the queue.
    pop = defer.DeferredQueue.get

    def add(self, item):
        if item not in self.pending:
            self.put(item)

    def discard(self, item):
        if item in self.pending:
            self.pending.remove(item)
