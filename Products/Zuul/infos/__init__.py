###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.interface import implements
from zope.component import adapts
from Products.Zuul.interfaces import IInstanceInfo, IInstance
from Products.Zuul.facades import InfoBase

class InstanceInfo(InfoBase):
    implements(IInstanceInfo)
    adapts(IInstance)

    def __init__(self, obj):
        self._object = obj

    @property
    def id(self):
        return self._object.id

    @property
    def device(self):
        return self._object.device().titleOrId()

    @property
    def name(self):
        return self._object.name()

    @property
    def monitor(self):
        return self._object.zMonitor

    @property
    def status(self):
        statusCode = self._object.getStatus()
        return self._object.convertStatus(statusCode)
