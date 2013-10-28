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

    def __init__(self, data):
        self._data = data

    @property
    def id(self):
        return self._object.id

    @property
    def name(self):
        return self._object.name

    @property
    def uid(self):
        return ''

    @property
    def description(self):
        return self._object.description

    @property
    def enabled(self):
        return self._object.status == "ENABLED"

    @property
    def processId(self):
        return self._object.processId


@implementer(IApplicationLogInfo)
class ApplicationLogInfo(object):

    def __init__(self, data):
        self._data = data

    @property
    def id(self):
        return self._data.id

    @property
    def name(self):
        return self._data.name

    @property
    def uid(self):
        return ''

    @property
    def lines(self):
        return self._data.lines

    def last(self, count):
        return self._data.lines[-count:]
