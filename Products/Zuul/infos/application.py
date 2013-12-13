##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from datetime import datetime
from zope.interface import implementer
from Products.Zuul.interfaces import IApplicationInfo


@implementer(IApplicationInfo)
class ApplicationInfo(object):
    """
    Info object for the applications returned from the control
    plane.
    """

    def __init__(self, app):
        """
        Initialize an instance of ApplicationInfo.

        :param IApplication application: The application.
        """
        self._object = app
        self._children = []

    @property
    def id(self):
        return self._object.id

    @property
    def name(self):
        return self._object.name

    @property
    def text(self):
        return self._object.name

    @property
    def type(self):
        return "daemon"

    @property
    def uid(self):
        return self._object.id

    @property
    def tags(self):
        return self._object.tags
    
    def getParentServiceId(self):
        return self._object.parentServiceId
    
    @property
    def description(self):
        return self._object.description

    @property
    def qtip(self):
        return self._object.description

    @property
    def autostart(self):
        return self._object.autostart

    @property
    def isRestarting(self):
        return self._object.state == "RESTARTING"

    @property
    def uptime(self):
        started = self._object.startedAt
        if started:
            return str(datetime.today() - started)

    @property
    def state(self):
        return str(self._object.state)

    @property
    def leaf(self):
        return len(self.children) == 0

    def addChild(self, child):
        self._children.append(child)

    @property
    def children(self):
        return self._children
