##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from zope.component import getUtility, getAdapter, getMultiAdapter
from zope.interface import implementer
from ZODB.transact import transact

from Products.Zuul.decorators import info
from Products.Zuul.interfaces import (
    IApplicationManager, IApplication, IApplicationLog
)
from Products.Zuul.utils import unbrain
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

    def query(self):
        """
        Returns a sequence of IApplication objects.
        """
        result = self._svc.queryServices()
        if not result:
            return ()
        return tuple(ServiceApplication(instance) for instance in result)

    def get(self, name, default=None):
        """
        Returns the IApplicationInfo object of the named application.
        """
        result = self._svc.queryServices(name=name)
        if not result:
            return default
        instance = list(result)[0]
        return ServiceApplication(instance)


@implementer(IApplication)
class ServiceApplication(object):
    """
    """

    def __init__(self, instance):
        self._instance = instance
        self._svc = getUtility(IControlPlaneClient)

    @property
    def id(self):
        return self._instance.id

    @property
    def name(self):
        return self._instance.name

    @property
    def description(self):
        return self._instance.description

    @property
    def processId(self):
        return self._instance.processId

    @property
    def state(self):
        return self._instance.state

    @property
    def enabled(self):
        return self._instance.status == self._instance.STATUS.AUTO

    @enabled.setter
    def enabled(self, value):
        value = bool(value)
        self._instance.status = self._instance.STATUS[value]
        self._svc.updateInstance(self._instance)

    @property
    def processId(self):
        return self._instance.processId

    def start(self):
        """
        Starts the named application.
        """
        self._instance.state = "RUN"
        self._svc.updateInstance(self._instance)

    def stop(self):
        """
        Stops the named application.
        """
        self._instance.state = "STOP"
        self._svc.updateInstance(self._instance)

    def restart(self):
        """
        Restarts the named application.
        """
        self._instance.state = self._instance.STATE.RESTART
        self._svc.updateInstance(self._instance)

    def getLog(self):
        """
        Retrieves the log of the named application.

        :rtype: Sequence of strings.
        """
        return getAdapter(self._instance, IApplicationLog)

    def getConfig(self):
        """
        Retrieves the IConfig object of the named application.
        """
        data = self._svc.getConfiguration(self._instance.id)
        return Config

    def setConfig(self, config):
        """
        Sets the config of the named application.
        """
        instance = self._getInstance(self.name)

    def _getInstance(self):
        result = self._svc.get(self._instance.id)
        if not result:
            raise UnknownApplicationError(self.name)
        self._instance = list(result)[0]


@implementer(IApplicationLog)
class ServiceApplicationLog(object):
    """
    """

    def __init__(self, instance):
        self._instance = instance
        self._svc = getUtility(IControlPlaneClient)

    def first(self, count):
        """
        Returns a sequence containing the first count lines of the log.

        :rtype: A sequence of strings.
        """
        result = self._svc.getInstanceLog(
            instance.id, start=0, end=count
        )
        return result.data

    def last(self, count):
        """
        Returns a sequence containing the last count lines of the log.

        :rtype: A sequence of strings.
        """
        result = self._svc.getInstanceLog(instance.id, start=-count)
        return result.data

    def slice(self, start, end):
        """
        Returns a sequence of lines from start line to end line in the log.

        :rtype: A sequence of strings.
        """
        result = self._svc.getInstanceLog(instance.id, start=start, end=end)
        return result.data
