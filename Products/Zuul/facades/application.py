##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from zope.component import getAdapter, getMultiAdapter
from zope.interface import implementer
from ZODB.transact import transact

from Products.Zuul import getFacade
from Products.Zuul.decorators import info
from Products.Zuul.interfaces import (
    IApplicationManager, IApplicationInfo, IApplicationLog
)
from Products.Zuul.utils import unbrain


@implementer(IApplicationManager)
class ServiceApplicationManager(object):
    """
    """

    def __init__(self):
        """
        """
        self._svc = getFacade(IControlService)

    def query(self):
        """
        Returns a sequence of IApplicationInfo objects.
        """
        result = self._svc.query()
        if not result:
            return ()
        return tuple(
            getAdapter(instance, IApplication) for instance in result
        )

    def get(self, name, default=None):
        """
        Returns the IApplicationInfo object of the named application.
        """
        result = self._svc.query(name=name)
        if not result:
            return default
        instance = list(result)[0]
        return getAdapter(instance, IApplication)


@implementer(IApplication)
class ServiceApplication(object):
    """
    """

    def __init__(self, instance):
        self._instance = instance
        self._svc = getFacade(IControlService)

    @property
    def description(self):
        return self._object.description

    @property
    def enabled(self):
        return self._object.status

    @enabled.setter
    def enabled(self, value):
        self._instance.status = bool(value)
        self._svc.updateInstance(self._instance)

    @property
    def processId(self):
        return self._object.processId

    def start(self):
        """
        Starts the named application.
        """
        instance = self._getInstance(name)
        instance.state = instance.states.START
        self._svc.updateInstance(instance)

    def stop(self, name):
        """
        Stops the named application.
        """
        instance = self._getInstance(name)
        instance.state = instance.states.STOP
        self._svc.updateInstance(instance)

    def restart(self, name):
        """
        Restarts the named application.
        """
        instance = self._getInstance(name)
        instance.state = instance.states.RESTART
        self._svc.updateInstance(instance)

    def getLog(self, name):
        """
        Retrieves the log of the named application.

        :rtype: Sequence of strings.
        """
        instance = self._getInstance(name)
        return getAdapter(instance, IApplicationLog)

    def getConfig(self, name):
        """
        Retrieves the IConfig object of the named application.
        """
        instance = self._getInstance(name)
        data = self._svc.getConfiguration(instance.id)
        return Config

    def setConfig(self, name, config):
        """
        Sets the config of the named application.
        """
        instance = self._getInstance(name)

    def _getInstance(self):
        result = self._svc.get(self._instance.id)
        if not result:
            raise UnknownApplicationError(name)
        self._instance = list(result)[0]


@implementer(IApplicationLog)
class ServiceApplicationLog(object):
    """
    """

    def __init__(self, instance):
        self._instance = instance
        self._svc = getFacade(IControlService)

    def first(self, count):
        """
        Returns a sequence containing the first count lines of the log.

        :rtype IApplicationLogInfo: The log data.
        """
        result = self._svc.getInstanceLog(
            instance.id, start=0, end=count
        )
        return getAdapter(result.data, IApplicationLogInfo)

    def last(self, count):
        """
        Returns a sequence containing the last count lines of the log.

        :rtype IApplicationLogInfo: The log data.
        """
        result = self._svc.getInstanceLog(instance.id, start=-count)
        return getAdapter(result.data, IApplicationLogInfo)

    def slice(self, start, end):
        """
        Returns a sequence of lines from start line to end line in the log.

        :rtype IApplicationLogInfo: The log data.
        """
        result = self._svc.getInstanceLog(instance.id, start=start, end=end)
        return getAdapter(result.data, IApplicationLogInfo)
