##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import collections

from contextlib import contextmanager
from twisted.internet import defer

from Products.ZenUtils.Logger import getLogger


class WorkerPool(
        collections.Container, collections.Iterable, collections.Sized):
    """Pool of ZenHubWorker RemoteReference objects.
    """

    def __init__(self):
        """
        """
        self.__available = []  # Workers (by ID) available for work
        self.__workers = {}  # Worker refs by worker ID
        self.__services = {}  # Service refs by worker

    def add(self, worker):
        """Add a worker to the pool.

        Note: the worker is expected to have a 'workerId' attribute.

        @param worker {RemoteReference} A reference to the remote worker
        """
        assert type(worker) is not WorkerRef, "worker may be not a WorkerRef"
        wId = worker.workerId
        if self.__workers.get(wId) is worker:
            return
        self.__workers[wId] = worker
        self.__services[wId] = ServiceRegistry(worker)
        if wId not in self.__available:
            self.__available.append(wId)

    def remove(self, worker):
        """Remove a worker from the pool.

        Note: the worker is expected to have a 'workerId' attribute.

        @param worker {RemoteReference} A reference to the remote worker
        """
        assert type(worker) is not WorkerRef, "worker may be not a WorkerRef"
        wId = worker.workerId
        if wId not in self.__workers:
            return
        if self.__workers[wId] is not worker:
            return  # Stale worker, already removed
        del self.__workers[wId]
        del self.__services[wId]
        if wId in self.__available:
            self.__available.remove(wId)

    def __contains__(self, worker):
        """Returns True if worker is registered, else False is returned.

        Note: the worker is expected to have a 'workerId' attribute.

        @param worker {RemoteReference} A reference to the remote worker
        """
        return self.__workers.get(worker.workerId) is worker

    def __len__(self):
        return len(self.__workers)

    def __iter__(self):
        return (
            self.__makeref(wId)
            for wId, worker in self.__workers.iteritems()
            if worker is not None
        )

    @property
    def available(self):
        """Returns the number of workers available for work.
        """
        return len(self.__available)

    @contextmanager
    def borrow(self):
        """Context manager that returns a worker available for work.

        with self.__workers.borrow() as worker:
            # do stuff with worker.

        If no worker is available for work, an IndexError is raised.
        """
        if not len(self.__available):
            raise IndexError("No worker available")
        wId = self.__available.pop(0)
        try:
            worker = self.__workers[wId]
            yield self.__makeref(wId)
        finally:
            if self.__workers.get(wId) is worker:
                self.__available.append(wId)

    def __makeref(self, workerId):
        return WorkerRef(self.__workers[workerId], self.__services[workerId])


class ServiceRegistry(object):
    """
    """

    def __init__(self, worker):
        """Initialize a ServiceRegistry instance.
        """
        self.__services = {}  # (service-name, monitor): service-ref
        self.__worker = worker

    def get(self, key, default=None):
        return self.__services.get(key, default)

    def __contains__(self, key):
        return key in self.__services

    @defer.inlineCallbacks
    def lookup(self, service, monitor):
        """Asynchronous retrieval of a service reference.
        """
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
        """
        """
        self.__worker = worker
        self.__services = services
        self.__log = getLogger("zenhub", self)

    @property
    def ref(self):
        return self.__worker

    @property
    def services(self):
        return self.__services

    def __getattr__(self, name):
        return getattr(self.__worker, name)

    @defer.inlineCallbacks
    def run(self, job):
        """Execute the job.

        @param job {ServiceCallJob} Details on the RPC method to invoke.
        @raises Exception if an error occurs while attempting to
            execute a remote procedure call.  An RPC error may occur while
            retrieving the remote service reference or when invoking the
            job specified method on the remote service reference.
        """
        try:
            service = yield self.__services.lookup(job.service, job.monitor)
        except Exception as ex:
            self.__log.error(
                "(worker %s) Failed to retrieve service '%s': %s",
                self.__worker.workerId, job.service, ex,
            )
            raise

        try:
            result = yield service.callRemote(
                job.method, *job.args, **job.kwargs
            )
            defer.returnValue(result)
        except Exception as ex:
            self.__log.error(
                "(worker %s) Failed to execute %s.%s: %s",
                self.__worker.workerId, job.service, job.method, ex,
            )
            raise
