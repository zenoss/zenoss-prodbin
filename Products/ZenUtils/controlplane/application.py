##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
IApplication* control-plane implementations.
"""

import logging
import os
from functools import wraps
from Products.ZenUtils.controlplane import getConnectionSettings
from collections import Sequence, Iterator
from zope.interface import implementer

from Products.ZenUtils.application import (
    IApplicationManager, IApplication, IApplicationLog,
    IApplicationConfiguration, ApplicationState
)

from .client import ControlPlaneClient
from .runstates import RunStates

LOG = logging.getLogger("zen.controlplane")


@implementer(IApplicationManager)
class DeployedAppLookup(object):
    """
    Query the control-plane for Zenoss application services.
    """

    # The class of the Control Plane client
    clientClass = ControlPlaneClient

    @staticmethod
    def _applicationClass():
        return DeployedApp

    def __init__(self):
        settings = getConnectionSettings()
        self._client = self.clientClass(**settings)
        # Cache RunState objects in order to persist state between requests
        #  to support RESTARTING state.
        self._statecache = {}

    def getTenantId(self):
        """
        Returns the tenant ID from the environment.
        """
        tenantID_env = "CONTROLPLANE_TENANT_ID"
        return os.environ.get(tenantID_env)

    def query(self, name=None, tags=None, monitorName=None):
        """
        Returns a sequence of IApplication objects.
        """
        tenant_id = self.getTenantId()
        if tenant_id is None:
            LOG.error("ERROR: Could not determine the tenantID from the "
                      "environment")
            return ()

        # Retrieve services according to name and tags.
        result = self._client.queryServices(name=name, tags=tags, tenantID=tenant_id)
        if not result:
            return ()

        # If monitorName is specified, filter for services which are
        # parented by the specified monitor.
        if monitorName:
            # Replace "daemon" with "-daemon" to exclude services which are
            # applications.
            tags = set(tags) - set(["daemon"])
            tags.add("-daemon")
            parents = self._client.queryServices(name=monitorName, tags=list(tags), tenantID=tenant_id)
            # If the monitor name wasn't found, return an empty sequence.
            if not parents:
                return ()
            parentId = parents[0].id  # Get control-plane service ID
            result = (
                svc for svc in result if svc.parentId == parentId
            )

        return tuple(self._getApp(service) for service in result)

    def get(self, id, default=None):
        """
        Retrieve the IApplication object of the identified application.
        The default argument is returned if the application doesn't exist.
        """
        service = self._client.getService(id)
        if not service:
            return default

        return self._getApp(service)

    def _getApp(self, service):
        runstate = self._statecache.get(service.id)
        if not runstate:
            runstate = RunStates()
            self._statecache[service.id] = runstate
        return self._applicationClass()(service, self._client, runstate)


@implementer(IApplication)
class DeployedApp(object):
    """
    Control and interact with the deployed app via the control plane.
    """
    UNKNOWN_STATUS = type('SENTINEL', (object,), {'__nonzero__': lambda x: False})()

    def __init__(self, service, client, runstate):
        self._client = client
        self._runstate = runstate
        self._service = service
        self._status = DeployedApp.UNKNOWN_STATUS

    def _initStatus(fn):
        """
        Decorator which calls updateStatus if status is uninitialized
        """
        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            if self._status == DeployedApp.UNKNOWN_STATUS:
                self.updateStatus(*args, **kwargs)
            return fn(self)
        return wrapper

    def updateStatus(self):
        """
        Retrieves the current running instance of the application.
        """
        result = self._client.queryServiceStatus(self._service.id)
        instanceId_0 = [i for i in result.itervalues() if i.instanceId == 0]
        self._status = instanceId_0[0] if instanceId_0 else None
        if self._status is None:
            self._runstate.lost()
        else:
            self._runstate.found(self._status)

    @property
    def id(self):
        return self._service.id

    @property
    def name(self):
        return self._service.name

    @property
    @_initStatus
    def hostId(self):
        return self._status.hostId if self._status else None

    @property
    def description(self):
        return self._service.description

    @property
    @_initStatus
    def state(self):
        return self._runstate.state

    @property
    @_initStatus
    def startedAt(self):
        """
        When the service started.  Returns None if not running.
        """
        return self._status.startedAt if self._status else None

    @property
    def tags(self):
        return self._service.tags or []

    @property
    @_initStatus
    def log(self):
        """
        The log of the application.

        :rtype str:
        """
        if self._status:
            return DeployedAppLog(self._status, self._client)

    @property
    def autostart(self):
        """
        Boolean property indicating whether the application automatically
        starts.
        """
        return self._service.launch == self._service.LAUNCH_MODE.AUTO

    @autostart.setter
    def autostart(self, value):
        value = self._service.LAUNCH_MODE.AUTO \
            if bool(value) else self._service.LAUNCH_MODE.MANUAL
        self._service.launch = value
        # TODO: remove this; instead call 'facade.updateService(id)' from Products/Zuul/routers/application.py
        self._client.updateService(self._service)

    @property
    def configurations(self):
        """
        """
        return  _DeployedAppConfigList(self._service, self._client)

    @_initStatus
    def start(self):
        """
        Starts the application.
        """
        priorState = self._runstate.state
        self._runstate.start()
        if priorState != self._runstate.state:
            LOG.info("[%x] STARTING APP", id(self))
            self._service.desiredState = self._service.STATE.RUN
            self._client.startService(self._service.id)

    @_initStatus
    def stop(self):
        """
        Stops the application.
        """
        priorState = self._runstate.state
        self._runstate.stop()
        if priorState != self._runstate.state:
            LOG.info("[%x] STOPPING APP", id(self))
            self._service.desiredState = self._service.STATE.STOP
            self._client.stopService(self._service.id)

    def restart(self):
        """
        Restarts the application.
        """
        # Make sure the current state is known.
        self.updateStatus()
        # temporary until proper 'reset' functionality is
        # available in controlplane.
        priorState = self._runstate.state
        self._runstate.restart()
        if priorState != self._runstate.state:
            LOG.info("[%x] RESTARTING APP", id(self))
            if self._status:
                self._client.killInstance(
                    self._status.hostId, self._status.id
                )
            else:
                self._service.desiredState = self._service.STATE.RUN
                self._client.startService(self._service.id)

    def update(self):
        """
        """
        self._client.updateService(self._service)


class _DeployedAppConfigList(Sequence):
    """
    Helper class implementing the Sequence protocol.  Instances of
    this class are the object returned by the IApplication's
    'configurations' property.
    """

    def __init__(self, service, client):
        self._service = service
        self._client = client

    def __getitem__(self, index):
        """
        Return the selected configuration file(s) as indicated by
        the index.  Slice notation is supported.
        """
        # Note: 'index' can be a slice object, but since it's forwarded
        # to the list's __getitem__ method, don't worry about it.
        values = self._service.configFiles.values()
        data = values.__getitem__(index)
        return DeployedAppConfig(self._service, self._client, data)

    def __len__(self):
        """
        Return the number of configuration files.
        """
        return len(self._service.configFiles)

    def __iter__(self):
        """
        Return an iterator that produces DeployedAppConfig objects.
        """
        return _ConfigIterator(self._service, self._client)


class _ConfigIterator(Iterator):
    """
    Helper class to implement iteration of the list of
    IApplicationConfiguration objects.
    """

    def __init__(self, service, client):
        self._service = service
        self._client = client
        if not self._service.configFiles is None:
            self._iter = iter(self._service.configFiles.values())
        else:
            self._iter = iter([])

    def __iter__(self):
        return self

    def next(self):
        return DeployedAppConfig(
            self._service, self._client, self._iter.next())


@implementer(IApplicationConfiguration)
class DeployedAppConfig(object):
    """
    """

    def __init__(self, service, client, config):
        self._service = service
        self._client = client
        self._config = config

    @property
    def filename(self):
        """Full path filename of configuration."""
        return self._config.get("Filename")

    @property
    def content(self):
        """Raw contents of the configuration file."""
        return self._config.get("Content")

    @content.setter
    def content(self, content):
        self._config["Content"] = content


@implementer(IApplicationLog)
class DeployedAppLog(object):
    """
    """

    def __init__(self, instance, client):
        self._status = instance
        self._client = client

    def last(self, count):
        """
        Returns last count lines of the application log.

        :rtype str:
        """
        result = self._client.getInstanceLog(
            self._status.serviceId, self._status.id
        )
        return result.split("\n")[-count:]


__all__ = (
    "DeployedApp", "DeployedAppConfig", "DeployedAppLog", "DeployedAppLookup"
)
