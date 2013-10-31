##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.component import getUtility
from zope.interface import implementer

from Products.Zuul.interfaces import (
    IApplicationManager, IApplication, IApplicationLog
)
from Products.ZenUtils.controlplane.interfaces import IControlPlaneClient


@implementer(IApplicationManager)
class ServiceApplicationManager(object):
    """
    """

    def __init__(self, dataroot):
        """
        """
        self._dmd = dataroot
        self._svc = getUtility(IControlPlaneClient)

    def query(self, name=None):
        """
        Returns a sequence of IApplication objects.
        """
        args = {"name": name} if name else {}
        result = self._svc.queryServices(**args)
        if not result:
            return ()
        return tuple(ServiceApplication(service) for service in result)

    def get(self, serviceId, default=None):
        """
        Returns the IApplicationInfo object of the identified application.
        """
        service = self._svc.getService(serviceId)
        if not service:
            return default
        return ServiceApplication(service)


@implementer(IApplication)
class ServiceApplication(object):
    """
    """

    def __init__(self, service):
        self._service = service
        self._instance = None
        self._svc = getUtility(IControlPlaneClient)

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
        result = self._svc.queryServiceInstances(self._service.id)
        self._instance = result[0] if result else None
        desired = self._service.desiredState
        if desired == self._service.STATE.RUN:
            return "RUNNING" if self._instance else "STARTING"
        elif desired == self._service.STATE.STOP:
            return "STOPPED" if not self._instance else "STOPPING"
        return "UNKNOWN"

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
        return ServiceApplicationLog(self._instance)

    @property
    def autostart(self):
        return self._service.launch == self._service.LAUNCH_MODE.AUTO

    @autostart.setter
    def autostart(self, value):
        value = self._service.LAUNCH_MODE.AUTO \
            if bool(value) else self._service.LAUNCH_MODE.MANUAL
        self._service.launch = value
        self._svc.updateService(self._service)

    def getConfig(self):
        """
        Retrieves the IConfig object of the named application.
        """
        #data = self._svc.getConfiguration(self._service.id)
        #return Config

    def setConfig(self, config):
        """
        Sets the config of the named application.
        """
        pass

    def start(self):
        """
        Starts the named application.
        """
        self._service.desiredState = self._service.STATE.RUN
        self._svc.updateService(self._service)

    def stop(self):
        """
        Stops the named application.
        """
        self._service.desiredState = self._service.STATE.STOP
        self._svc.updateService(self._service)

    def restart(self):
        """
        Restarts the named application.
        """
        # temporary until proper 'reset' functionality is
        # available in controlplane.
        if self._instance:
            self._svc.killInstance(self._instance.id)


@implementer(IApplicationLog)
class ServiceApplicationLog(object):
    """
    """

    def __init__(self, instance):
        self._instance = instance
        self._svc = getUtility(IControlPlaneClient)

    def last(self, count):
        """
        Returns last count lines of the application log.

        :rtype str:
        """
        result = self._svc.getInstanceLog(self._instance.id)
        loglines = result.split("\n")
        return '\n'.join(loglines[:-count])
