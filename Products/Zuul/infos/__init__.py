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
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.Zuul.interfaces import IInfo

class InfoBase(object):
    implements(IInfo)
    adapts(ZenModelRM)

    def __init__(self, object):
        self._object = object

    @property
    def uid(self):
        _uid = getattr(self, '_v_uid', None)
        if _uid is None:
            _uid = self._v_uid = '/'.join(self._object.getPrimaryPath())
        return _uid

    @property
    def id(self):
        return self._object.id

    def getName(self):
        return self._object.titleOrId()

    def setName(self, name):
        self._object.setTitle(name)

    name = property(getName, setName)

    def getDescription(self):
        return self._object.description

    def setDescription(self, value):
        self._object.description = value

    description = property(getDescription, setDescription)

    def __repr__(self):
        return '<%s Info "%s">' % (self._object.__class__.__name__, self.id)

