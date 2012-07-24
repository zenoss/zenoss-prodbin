##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import implements
from zope.component import adapts
from OFS.CopySupport import CopyError
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.Zuul.interfaces import IInfo
from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_CLEAR, SEVERITY_INFO, SEVERITY_DEBUG, SEVERITY_WARNING, \
    SEVERITY_ERROR, SEVERITY_CRITICAL
from Products.Zuul import getFacade
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.Zuul.utils import safe_hasattr as hasattr


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
        try:
            self._object.rename(newId)
        except CopyError, e:
            raise Exception("Name '%s' is invalid or already in use." % newId)

    def __repr__(self):
        return '<%s Info "%s">' % (self._object.__class__.__name__, self.id)


class LockableMixin(object):

    @property
    def locking(self):
        return {
            'updates': self._object.isLockedFromUpdates(),
            'deletion': self._object.isLockedFromDeletion(),
            'events': self._object.sendEventWhenBlocked()}


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

    def getEventSeverities(self):
        if self._eventSeverities is None:
            zep = getFacade('zep')
            # ZEP facade returns CRITICAL/ERROR/WARNING by default - need to include INFO for rainbow on
            # device detail page.
            severities = (SEVERITY_CRITICAL, SEVERITY_ERROR, SEVERITY_WARNING, SEVERITY_INFO)
            self.setEventSeverities(zep.getEventSeveritiesByUuid(self.uuid, severities=severities))
        return self._eventSeverities

    @property
    def events(self):
        severities = self.getEventSeverities()
        zep = getFacade('zep')
        return dict((zep.getSeverityName(sev).lower(), counts) for (sev, counts) in severities.iteritems())

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


class BulkLoadMixin(object):

    def setBulkLoadProperty(self, name, value):
        """
        Sets a property that can later be retrieved
        by the marshaller. You will have to check
        the property manually. If set twice it will
        overwrite the previous entry.
        """
        if not hasattr(self, '_props'):
            self._props = {}
        self._props[name] = value

    def getBulkLoadProperty(self, name):
        """
        Will return None if not present
        otherwise the cached value set from
        the setBulkLoadProperty method
        """
        if not hasattr(self, '_props'):
            return None
        return self._props.get(name)
