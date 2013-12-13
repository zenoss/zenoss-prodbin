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

    def _isCollector(self, node):
        """
        Determines if this application represents a collector by looking at the
        tags.
        """
        tags = node.tags or []
        return 'collector' in tags and not 'daemon' in tags

    def _replaceNodeWithInfoObject(self, node):
        return ITreeNode(self._dmd.Monitors.getPerformanceMonitor(node.name))

    def _shouldReplaceNode(self, node):
        """
        Helper method for the replace Nodes method. This determines if this
        application node should be replaced by something more specific, like
        a collector info object.
        """
        return self._isCollector(node)

    def _replaceNodes(self, roots):
        """
        This method takes a tree structure of application info objects
        and figures out which ones should be replaced with collector nodes.
        This is so that on the UI we can figure
        """
        toReplace = []
        for node in roots:
            if self._shouldReplaceNode(node):
                toReplace.append(node)

        # replace nodes
        for node in toReplace:
            roots = [n for n in roots if n.id != node.id]
            newNode = self._replaceNodeWithInfoObject(node)
            newNode._children = node._children
            roots.append(newNode)

        # recursively replace the child nodes
        for node in roots:
            node._children = self._replaceNodes(node._children)

        return roots

    def getTree(self):
        """
        Returns all of the collectors and daemons in tree
        form that is marshallable to be used by the UI.
        """
        # get all services. This will pull in everything including Collectors etc
        services = self.query()
        tree = dict()
        for service in services:
            tree[service.id] = IInfo(service)

        # organize them into a tree
        for id, service in tree.iteritems():
            if service.getParentServiceId():                
                parent = tree[service.getParentServiceId()]
                parent.addChild(service)
                             
        roots = [service for service in tree.values() if not service.getParentServiceId()]
        #roots = self._replaceNodes(roots)
        return roots

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
