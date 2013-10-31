##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import implementer
from Products.Zuul.interfaces import IApplicationInfo, IApplicationLogInfo


@implementer(IApplicationInfo)
class ApplicationInfo(object):
    """
    """

    def __init__(self, application):
        """
        Initialize an instance of ApplicationInfo.

        :param IApplication application: The IApplication facade.
        """
        self._object = application

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
    def uid(self):
        return self._object.id

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
        return str(self._object.state) == "RESTARTING"

    @property
    def state(self):
        return str(self._object.state)

    @property
    def leaf(self):
        return True

    @property
    def children(self):
        return []


@implementer(IApplicationLogInfo)
class ApplicationLogInfo(object):
    """
    """

    def __init__(self, applicationlog):
        """
        Initialize an instance of ApplicationLogInfo.

        :param IApplicationLog applog: The IApplicationLog facade.
        """
        self._applicationlog = applicationlog

    @property
    def lines(self):
        """
        :rtype: A sequence of strings.
        """
        return self._applicationlog.last(100)
