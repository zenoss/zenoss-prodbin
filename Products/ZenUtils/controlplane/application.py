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

from zope.interface import implementer

from Products.ZenUtils.application import (
    IApplicationManager, IApplication, IApplicationLog,
    ApplicationState
)

from .client import ControlPlaneClient
from .runstates import RunStates

LOG = logging.getLogger("zen.controlplane")


@implementer(IApplicationManager)
class DeployedAppLookup(object):
    """
    Query the control-plane for Zenoss application services.
    """

    def __init__(self):
        self._client = ControlPlaneClient()
        self._appcache = {}

    def query(self, name=None):
        """
        Returns a sequence of IApplication objects.
        """
        result = self._client.queryServices(name=name, tags=["daemon"])
        if not result:
            return ()
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

    def getConfig(self):
        """
        Retrieves the IConfig object of the application.
        """
        #data = self._client.getConfiguration(self._service.id)
        #return Config

    def setConfig(self, config):
        """
        Sets the config of the application.
        """
        pass

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
