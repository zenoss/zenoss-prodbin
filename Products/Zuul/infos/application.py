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
        self._application = application

    @property
    def id(self):
        return ''

    @property
    def name(self):
        return self._application.name

    @property
    def uid(self):
        return ''

    @property
    def description(self):
        return self._application.description

    @property
    def enabled(self):
        return self._application.enabled

    @property
    def processId(self):
        return self._application.processId


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
