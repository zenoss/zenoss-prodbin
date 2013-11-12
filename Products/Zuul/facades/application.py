##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
from zope.component import getUtility
from zope.interface import implementer

from Products.ZenUtils.application import IApplicationManager
from Products.Zuul.interfaces import IApplicationFacade

LOG = logging.getLogger("Zuul.facades")


@implementer(IApplicationFacade)
class ApplicationFacade(object):
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
        result = self._svc.query(name=name, tags=["daemon"])
        if not result:
            return ()
        return tuple(result)

    def get(self, id, default=None):
        """
        Returns the IApplicationFacade object of the identified application.
        """
        app = self._svc.get(id, default)
        if not app:
            return default
        return app

    def getLog(self, id, lastCount=None):
        app = self._svc.get(id)
        if not app:
            raise RuntimeError("No such application '%s'" % (id,))
        if app.log:
            count = lastCount if lastCount else 200
            return '\n'.join(app.log.last(count))
        else:
            return ''  # not running, so no log.

    def start(self, appId):
        """
        Starts the application.
        """
        app = self._svc.get(appId)
        if app:
            app.start()

    def stop(self, appId):
        """
        Stops the application.
        """
        app = self._svc.get(appId)
        if app:
            app.stop()

    def restart(self, appId):
        """
        Restarts the application.
        """
        app = self._svc.get(appId)
        if app:
            app.restart()
