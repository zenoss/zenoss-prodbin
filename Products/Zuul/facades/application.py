##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import copy
import logging
from datetime import datetime
from zope.component import getUtility
from zope.interface import implementer

from Products.Zuul.interfaces import (
    IApplicationManagerFacade, IApplicationFacade
)
from Products.ZenUtils.application import IApplicationManager

LOG = logging.getLogger("Zuul.facades")


@implementer(IApplicationManagerFacade)
class ApplicationManagerFacade(object):
    """
    """

    def __init__(self, dataroot):
        """
        """
        self._dmd = dataroot
        self._svc = getUtility(IApplicationManager)

    def query(self, name=None):
        """
        Returns a sequence of IApplicationFacade objects.
        """
        args = {"name": name} if name else {}
        result = self._svc.query(**args)
        if not result:
            return ()
        return tuple(ApplicationFacade(app) for app in result)

    def get(self, id, default=None):
        """
        Returns the IApplicationFacade object of the identified application.
        """
        app = self._svc.get(id, default)
        if not app:
            return default
        return ApplicationFacade(app)


@implementer(IApplicationFacade)
class ApplicationFacade(object):
    """
    """

    def __init__(self, app):
        self._svc = getUtility(IApplicationManager)
        self._app = app

    @property
    def id(self):
        return self._app.id

    @property
    def name(self):
        return self._app.name

    @property
    def description(self):
        return self._app.description

    @property
    def state(self):
        return str(self._app.state)

    @property
    def startedAt(self):
        return self._app.startedAt

    @property
    def uptime(self):
        self.state
        started = self.startedAt
        if started:
            return str(datetime.today() - started)

    @property
    def autostart(self):
        return self._app.autostart

    @autostart.setter
    def autostart(self, value):
        self._app.autostart = value

    def getLog(self, lastCount=None):
        count = lastCount if lastCount else 200
        return '\n'.join(self._app.log.last(count))

    def getConfig(self):
        """
        Retrieves the IConfig object of the application.
        """
        pass

    def setConfig(self, config):
        """
        Sets the config of the application.
        """
        pass

    def start(self):
        """
        Starts the application.
        """
        self._app.start()

    def stop(self):
        """
        Stops the application.
        """
        self._app.stop()

    def restart(self):
        """
        Restarts the application.
        """
        self._app.restart()
