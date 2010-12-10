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
from Products.ZenEvents.EventManagerBase import EventManagerBase
from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_CLEAR, SEVERITY_INFO, SEVERITY_DEBUG
from Products.Zuul import getFacade
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier


def ProxyProperty(propertyName):
    """This uses a closure to make a getter and
    setter for the property (assuming it exists).
    """
    def setter(self, value):
        return setattr(self._object, propertyName, value)

    def getter(self):
        return getattr(self._object, propertyName)

    return property(getter, setter)

def ConfigProperty(configProp, configType):
        def getCP(self):
            return getattr(self._object, configProp)

        def setCP(self, setting):
            if self._object.hasProperty(configProp):
                self._object._updateProperty(configProp, setting)
            else:
                self._object._setProperty(configProp, setting, type=configType)
        return property(getCP, setCP)

class InfoBase(object):
    implements(IInfo)
    adapts(ZenModelRM)

    def __init__(self, object):
        super(InfoBase, self).__init__()
        self._object = object

    @property
    def objectProperties(self):
        """
        @returns the _properties from the object that
        this info is wrapping (ZenModel)
        """
        return self._object._properties

    @property
    def uid(self):
        _uid = getattr(self, '_v_uid', None)
        if _uid is None:
            _uid = self._v_uid = '/'.join(self._object.getPrimaryPath())
        return _uid

    @property
    def meta_type(self):
        return self._object.meta_type

    @property
    def inspector_type(self):
        return self._object.meta_type

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

    def rename(self, newId):
        """
        Call this when you wish to change the ID of the object, not just its title. This will recatalog it.
        """
        self._object.rename(newId)

    def __repr__(self):
        return '<%s Info "%s">' % (self._object.__class__.__name__, self.id)

class HasUuidInfoMixin(object):
    @property
    def uuid(self):
        return IGlobalIdentifier(self._object).getGUID()

class HasEventsInfoMixin(HasUuidInfoMixin):
    _eventSeverities = None
    _worstEventSeverity = None

    @property
    def severity(self):
        zep = getFacade('zep')
        if self._worstEventSeverity is None:
            self.setWorstEventSeverity(zep.getWorstSeverityByUuid(self.uuid))

        return zep.getSeverityName(self._worstEventSeverity).lower()

    @property
    def events(self):
        zep = getFacade('zep')
        if self._eventSeverities is None:
            self.setEventSeverities(zep.getEventSeveritiesByUuid(self.uuid))

        return dict((zep.getSeverityName(sev).lower(), count) for (sev, count) in self._eventSeverities.iteritems())

    def setWorstEventSeverity(self, severity):
        """
        Allow event severities to be set so they can be loaded in batches.
        """
        if severity in (SEVERITY_INFO, SEVERITY_DEBUG):
            # Ignore info and debug
            severity = SEVERITY_CLEAR

        self._worstEventSeverity = severity

    def setEventSeverities(self, severities):
        """
        Allow event severities to be set so they can be loaded in batches.
        """
        self._eventSeverities = severities
