###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.interface import implements
from Products.Zuul.interfaces import IOrganizerInfo, ILocationOrganizerInfo
from Products.Zuul.infos import InfoBase, HasEventsInfoMixin


class OrganizerInfo(InfoBase):
    implements(IOrganizerInfo)

    def setName(self, name):
        raise NotImplementedError('Can not set organizer name.')

    def _getDescription(self):
        return self._object.description

    def _setDescription(self, value):
        self._object.description = value

    description = property(_getDescription, _setDescription)


class LocationOrganizerInfo(OrganizerInfo, HasEventsInfoMixin):
    implements(ILocationOrganizerInfo)

    def getName(self):
        return self._object.getOrganizerName()

    def setName(self, name):
        self._object.setTitle(name)

    name = property(getName, setName)

    def _getAddress(self):
        return self._object.address

    def _setAddress(self, value):
        self._object.address = value

    address = property(_getAddress, _setAddress)
