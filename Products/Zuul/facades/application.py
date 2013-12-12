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
from Products import Zuul
from Products.Zuul.interfaces import IInfo, ITreeNode
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

    def _getDaemonNode(self):
        # this will create two "fake" nodes to organize
        # what we are displaying for the user.
        applications = self.query()
        infos = map(IInfo, applications)
        daemonNode = {
            'id': 'daemons',
            'visible': True,
            'leaf': False,
            'text': 'Daemons',
            'name': 'Daemons',
            'children': infos,
            'expanded': True
        }
        return daemonNode

    def _getCollectorNode(self):
        # collectors
        monitorFacade = Zuul.getFacade('monitors', self._dmd)
        collectors = monitorFacade.query()
        collectorData = Zuul.marshal(map(ITreeNode, collectors))

        collectorNode = {
            'id': 'collectors',
            'visible': True,
            'leaf': False,
            'text': 'Collectors',
            'name': 'Collectors',
            'children': collectorData,
            'expanded': True
        }
        return collectorNode

    def getTree(self):
        """
        """
        return [self._getDaemonNode(), self._getCollectorNode()]

    def query(self, name=None):
        """
        Returns a sequence of IApplication objects.
        """
        result = self._svc.query(name=name)
        if not result:
            return ()
        return tuple(result)

    def get(self, appId, default=None):
        """
        Returns the IApplicationFacade object of the identified application.
        """
        app = self._svc.get(appId, default)
        if not app:
            return default
        return app

    def getLog(self, appId, lastCount=None):
        """
        Retrieve the log of the identified application.  Optionally,
        a count of the last N lines to retrieve may be given.
        """
        app = self._svc.get(appId)
        if not app:
            raise RuntimeError("No such application '%s'" % (appId,))
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

__all__ = ("ApplicationFacade",)
