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
from collections import Sequence, Iterator
from zope.interface import implementer

from Products.ZenUtils.application import (
    IApplicationManager, IApplication, IApplicationLog,
    IApplicationConfiguration, ApplicationState
)
from Products.ZenUtils.GlobalConfig import globalConfToDict

from .client import ControlPlaneClient
from .runstates import RunStates

LOG = logging.getLogger("zen.controlplane")


def getConnectionSettings(options=None):
    if options is None:
        o = globalConfToDict()
    else:
        o = options
    settings = {
        "host": o.get("controlplane-host"),
        "port": o.get("controlplane-port"),
        "user": o.get("controlplane-user", "zenoss"),
        "password": o.get("controlplane-password", "zenoss"),
    }
    # allow these to be set from the global.conf for development but
    # give preference to the environment variables
    settings["user"] = os.getenv('CONTROLPLANE_SYSTEM_USER', settings['user'])
    settings["password"] = os.getenv('CONTROLPLANE_SYSTEM_PASSWORD', settings['password'])    
    return settings


@implementer(IApplicationManager)
class DeployedAppLookup(object):
    """
    Query the control-plane for Zenoss application services.
    """

    # The class of the Control Plane client
    clientClass = ControlPlaneClient

    def __init__(self):
        settings = getConnectionSettings()
        self._client = self.clientClass(**settings)        
        self._appcache = {}

    def query(self, name=None, tags=None, monitorName=None):
        """
        Returns a sequence of IApplication objects.
        """
        # Retrieve services according to name and tags.
        result = self._client.queryServices(name=name, tags=tags)
        if not result:
            return ()
        # If monitorName is specified, filter for services which are
        # parented by the specified monitor.
        if monitorName:
            # Replace "daemon" with "-daemon" to exclude services which are
            # applications.
            tags = set(tags) - set(["daemon"])
            tags.add("-daemon")
            parents = self._client.queryServices(monitorName, list(tags))
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
        app = self._appcache.get(service.id)
        if not app:
            app = DeployedApp(service, self._client)
            self._appcache[service.id] = app
        return app


@implementer(IApplication)
class DeployedApp(object):
    """
    Control and iteract with the deployed app via the control plane.
    """

    def __init__(self, service, client):
        self._client = client
        self._runstate = RunStates()
        self._service = service
        self._instance = None

    def _updateState(self):
        """
        Retrieves the current running instance of the application.
        """
        result = self._client.queryServiceInstances(self._service.id)
        instance = result[0] if result else None
        if instance is None and self._instance:
            self._runstate.lost()
        elif instance and (
                self._instance is None
                or self._runstate.state == ApplicationState.RESTARTING):
            self._runstate.found()
        self._instance = instance

    @property
    def id(self):
        return self._service.id

    @property
    def name(self):
        return self._service.name

    @property
    def description(self):
        return self._service.description

    @property
    def state(self):
        self._updateState()
        return self._runstate.state

    @property
    def startedAt(self):
        """
        When the service started.  Returns None if not running.
        """
        return self._instance.startedAt if self._instance else None

    @property
    def log(self):
        """
        The log of the application.

        :rtype str:
        """
        if not self._instance:
            self._updateState()
        if self._instance:
            return DeployedAppLog(self._instance, self._client)

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
        self._client.updateService(self._service)

    @property
    def configurations(self):
        """
        """
        return  _DeployedAppConfigList(self._service, self._client)

    def start(self):
        """
        Starts the application.
        """
        priorState = self._runstate.state
        self._runstate.start()
        if priorState != self._runstate.state:
            LOG.info("[%x] STARTING APP", id(self))
            self._service.desiredState = self._service.STATE.RUN
            self._client.updateService(self._service)

    def stop(self):
        """
        Stops the application.
        """
        priorState = self._runstate.state
        self._runstate.stop()
        if priorState != self._runstate.state:
            LOG.info("[%x] STOPPING APP", id(self))
            self._service.desiredState = self._service.STATE.STOP
            self._client.updateService(self._service)

    def restart(self):
        """
        Restarts the application.
        """
        # Make sure the current state is known.
        self._updateState()
        # temporary until proper 'reset' functionality is
        # available in controlplane.
        priorState = self._runstate.state
        self._runstate.restart()
        if priorState != self._runstate.state:
            LOG.info("[%x] RESTARTING APP", id(self))
            if self._instance:
                self._client.killInstance(
                    self._instance.hostId, self._instance.id
                )
            else:
                self._service.desiredState = self._service.STATE.RUN
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
        self._client.updateService(self._service)


@implementer(IApplicationLog)
class DeployedAppLog(object):
    """
    """

    def __init__(self, instance, client):
        self._instance = instance
        self._client = client

    def last(self, count):
        """
        Returns last count lines of the application log.

        :rtype str:
        """
        result = self._client.getInstanceLog(
            self._instance.serviceId, self._instance.id
        )
        return result.split("\n")[-count:]


__all__ = (
    "DeployedApp", "DeployedAppConfig", "DeployedAppLog", "DeployedAppLookup"
)
