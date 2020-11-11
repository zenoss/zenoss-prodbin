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
import os

from uuid import uuid4
from twisted.spread import pb

from ..PBDaemon import RemoteBadMonitor
from .exceptions import UnknownServiceError
from .utils import getLogger


class HubAvatar(pb.Avatar):
    """Manages the connection between clients and ZenHub."""

    def __init__(self, services, pools):
        """Initialize an instance of HubAvatar.

        :param services: The service manager
        :type services: .service.ServiceManager
        :param pools: Registry of zenhubworker remote references
        :type pools: Mapping[str, WorkerPool]
        """
        self.__services = services
        self.__pools = pools
        self.__log = getLogger(self)

    def perspective_ping(self):
        """Return 'pong'."""
        return 'pong'

    def perspective_getHubInstanceId(self):
        """Return the Control Center instance ID the running service."""
        return os.environ.get('CONTROLPLANE_INSTANCE_ID', 'Unknown')

    def perspective_getService(
            self, name, monitor=None, listener=None, options=None):
        """Return a reference to a ZenHub service.

        It also associates the service with a collector so that changes can be
        pushed back out to collectors.

        :param str name: The name of the service, e.g. "EventService"
        :param str monitor: The name of a collector, e.g. "localhost"
        :param listener: A remote reference to the client
        :type listener: twisted.spread.pb.RemoteReference
        :return: A reference to a service
        :rtype: .service.WorkerInterceptor
        """
        try:
            service = self.__services.getService(name, monitor)
        except RemoteBadMonitor:
            if self.__log.isEnabledFor(logging.DEBUG):
                self.__log.error("Monitor unknown monitor=%s", monitor)
            # This is a valid remote exception, so let it go through
            # to the collector daemon to handle
            raise
        except UnknownServiceError:
            self.__log.error("Service not found service=%s", name)
            raise
        except Exception as ex:
            self.__log.exception("Failed to load service service=%s", name)
            raise pb.Error(str(ex))
        else:
            if service is not None and listener:
                service.addListener(listener, options)
            return service

    def perspective_reportingForWork(self, worker, workerId, worklistId):
        """Allow a worker to register for work.

        :param worker: Reference to zenhubworker
        :type worker: twisted.spread.pb.RemoteReference
        :param int workerId: The worker's identifier
        :param str worklistId: The worker will work jobs from this worklist
        :rtype: None
        """
        worker.workerId = workerId
        worker.sessionId = uuid4()
        pool = self.__pools.get(worklistId)
        if pool is None:
            self.__log.error(
                "Worker asked to work unknown worklist "
                "worker=%s worklist=%s", workerId, worklistId,
            )
            raise pb.Error("No such worklist: %s" % worklistId)
        worker.queue_name = worklistId
        try:
            pool.add(worker)
        except Exception as ex:
            self.__log.exception("Failed to add worker worker=%s", workerId)
            raise pb.Error(
                "Internal ZenHub error: %s: %s" % (ex.__class__, ex),
            )
        self.__log.info(
            "Worker ready to work worker=%s session=%s worklist=%s",
            workerId, worker.sessionId.hex, worklistId,
        )

        def removeWorker(worker):
            pool = self.__pools.get(worker.queue_name)
            pool.remove(worker)
            self.__log.info(
                "Worker disconnected worker=%s session=%s",
                worker.workerId, worker.sessionId.hex,
            )

        worker.notifyOnDisconnect(removeWorker)
