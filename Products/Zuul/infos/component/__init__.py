###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
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
from Products.Zuul.interfaces import IComponentInfo, IComponent
from Products.Zuul.infos import InfoBase, ProxyProperty
from Products.Zuul.decorators import info

class ComponentInfo(InfoBase):
    implements(IComponentInfo)
    adapts(IComponent)

    @property
    @info
    def device(self):
        return self._object.device()

    @property
    def locking(self):
        return {
            'updates': self._object.isLockedFromUpdates(),
            'deletion': self._object.isLockedFromDeletion(),
            'events': self._object.sendEventWhenBlocked()
        }

    monitored = ProxyProperty('monitor')

    @property
    def status(self):
        statusCode = self._object.getStatus()
        return self._object.convertStatus(statusCode)

