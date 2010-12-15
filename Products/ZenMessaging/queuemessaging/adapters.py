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
from interfaces import IProtobufSerializer
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier, \
    IGloballyIdentifiable
from zenoss.protocols.protobufs import zep_pb2 as eventConstants
from zenoss.protocols.protobufs import model_pb2 as modelConstants
from time import time
from Products.ZenEvents.EventManagerBase import EventManagerBase
from Products.ZenMessaging.queuemessaging.interfaces import IModelProtobufSerializer

class ProtobufMappings:
    """
    Handles the mapping between zenoss constants
    and protobuf constants
    """
    event_statuses = {
        '0': eventConstants.STATUS_NEW,
        '1': eventConstants.STATUS_ACKNOWLEDGED,
        '2': eventConstants.STATUS_SUPPRESSED,
    }

    priorities = {
        '-1': eventConstants.SYSLOG_PRIORITY_DEBUG,
        '0': eventConstants.SYSLOG_PRIORITY_EMERG,
        '1': eventConstants.SYSLOG_PRIORITY_ALERT,
        '2': eventConstants.SYSLOG_PRIORITY_CRIT,
        '3': eventConstants.SYSLOG_PRIORITY_ERR,
        '4': eventConstants.SYSLOG_PRIORITY_WARNING,
        '5': eventConstants.SYSLOG_PRIORITY_NOTICE,
        '6': eventConstants.SYSLOG_PRIORITY_INFO,
    }

    severities = {
        '0': eventConstants.SEVERITY_CLEAR,
        '1': eventConstants.SEVERITY_DEBUG,
        '2': eventConstants.SEVERITY_INFO,
        '3': eventConstants.SEVERITY_WARNING,
        '4': eventConstants.SEVERITY_ERROR,
        '5': eventConstants.SEVERITY_CRITICAL,
        'CLEAR': eventConstants.SEVERITY_CLEAR,
        'DEBUG': eventConstants.SEVERITY_DEBUG,
        'INFO': eventConstants.SEVERITY_INFO,
        'WARNING': eventConstants.SEVERITY_WARNING,
        'ERROR': eventConstants.SEVERITY_ERROR,
        'CRITICAL': eventConstants.SEVERITY_CRITICAL,
    }

    def _setMapping(self, proto, field,  constant, mapping):
        """
        Checks to make sure we are sending a correct value and then
        updates the protobuf with the correct attribute.
        """
        if constant is not None:
            key = str(constant).upper()
            try:
                value = mapping[key]
            except KeyError:
                raise KeyError("%s is not a valid value of %s " % (constant, mapping))

            setattr(proto, field, value)

    def setSeverity(self, proto, severity):
        """
        Assumes the constant to be one of our severity mappings
        @type  proto: Protobuf
        @param proto: Protobuf we want the severity set on
        @type  severity: mixed
        @param severity: Event severity
        """
        self._setMapping(proto, 'severity', severity, self.severities)

    def setPriority(self, proto, priority):
        """
        Assumes the constant to be one of our priority mappings
        @type  proto: Protobuf
        @param proto: Protobuf we want the priority set on
        @type  priority: mixed
        @param priority: Event priority
        """
        self._setMapping(proto, 'syslog_priority', priority, self.priorities)


class ObjectProtobuf(object):
    """
    Base class for common methods on the protobuf populators
    """
    def __init__(self, obj):
        self.obj = obj

    def _getGUID(self, obj):
        return IGlobalIdentifier(obj).create()

    def autoMapFields(self, proto):
        """
        This maps fields that have the same name from the
        adapted object to the protobuf
        """
        if IGloballyIdentifiable.providedBy(self.obj):
            proto.uuid = self._getGUID(self.obj)
        fields = proto.DESCRIPTOR.fields

        # attempt to match the fields that are named the same
        for field in fields:
            # already set
            if field.name == "uuid":
                continue
            value = getattr(self.obj, field.name, None)
            # we want 0's
            if value is None:
                continue
            try:
                setattr(proto, field.name, value)
            except (AttributeError, TypeError):
                # likely a composite field that we will have to set manually
                continue


class DeviceProtobuf(ObjectProtobuf):
    """
    Fills up the properties of a device protobuf.
    """

    implements(IModelProtobufSerializer)

    @property
    def modelType(self):
        return "DEVICE"

    def fill(self, proto):
        self.autoMapFields(proto)
        proto.ip_address = self.obj.manageIp
        proto.production_state = self.obj.productionState
        proto.title = self.obj.titleOrId()
        # className
        deviceClass = self.obj.deviceClass()
        if deviceClass:
            proto.class_name_uuid = self._getGUID(deviceClass)
        proto.priority = self.obj.getPriority()
        # groups
        for group in self.obj.groups():
            proto.group_uuids.append(self._getGUID(group))

        # systems
        for system in self.obj.systems():
            proto.system_uuids.append(self._getGUID(system))

        # location
        if self.obj.location():
            proto.location_uuid = self._getGUID(self.obj.location())

        return proto


class OrganizerProtobuf(ObjectProtobuf):
    """
    Fills up the properties of an organizer protobuf.
    """

    implements(IModelProtobufSerializer)

    @property
    def modelType(self):
        return "ORGANIZER"

    def fill(self, proto):
        self.autoMapFields(proto)
        proto.title = self.obj.titleOrId()
        #get path minus first 3 '', 'zport', 'dmd'
        proto.path = '/'.join(self.obj.getPrimaryPath()[3:])
        return proto

class DeviceComponentProtobuf(ObjectProtobuf):
    """
    Fills up the properties of a Device Component
    """
    implements(IModelProtobufSerializer)

    @property
    def modelType(self):
        return "COMPONENT"

    def fill(self, proto):
        self.autoMapFields(proto)
        proto.title = self.obj.name()
        # use device protobuf to fill out our device property
        device = self.obj.device()
        if device:
            populator = DeviceProtobuf(device)
            populator.fill(proto.device)
        return proto


class EventProtobuf(ObjectProtobuf):
    """
    Fills up the properties of an event
    """

    implements(IProtobufSerializer)

    # event property, protobuf property
    fieldMappings = {
        'dedupid': 'fingerprint',
        'eventClassKey': 'event_class_key',
        'summary': 'summary',
        'message': 'message',
        'clearid': 'cleared_by_event_uuid',
        'monitor': 'monitor',
        'agent': 'agent',
        'eventGroup': 'event_group',
        'eventKey': 'event_key',
        'evid' : 'uuid',
    }

    def __init__(self, obj):
        ObjectProtobuf.__init__(self, obj)
        self.mapping = ProtobufMappings()

    def coerceToInteger(self, event, field, proto, protoField):
        """
        Some of our protobufs expect integers where the collectors deliver
        strings. This method forces them to be integers.
        """
        if hasattr(event, field):
            try:
                value = getattr(event, field)
                value = int(value)
                setattr(proto, protoField, value)
            except (ValueError, TypeError):
                # we can't convert, it so ignore it
                pass

    def safestr(self, s):
        """Defensive catchall to be sure that any string going into a protobuf can be
           decoded safely with 7-bit ASCII.  If any specialized encoding is desired, it 
           is the responsibility of the caller/sender to take care of it."""
        try:
            if isinstance(s, str):
                unicode(s, 'ascii')
        except UnicodeDecodeError:
            s = str(s.decode('ascii','ignore'))
        return s

    def setActor(self, proto):
        """
        This sets the "actor" attribute of the event.
        Can be any combination of device/component/service (including
        all three).
        """
        event = self.obj
        actor = proto.actor
        # there should always be a device
        actor.element_type_id = modelConstants.DEVICE
        actor.element_identifier = self.safestr(event.device)
        # there is not always a component
        if hasattr(event, 'component') and event.component:
            actor.element_sub_type_id = modelConstants.COMPONENT
            actor.element_sub_identifier = self.safestr(event.component)

    def fillDetails(self, proto):
        """
        These are just extra fields on the event. The specific
        fields are defined in "self.detailFields"
        """
        event = self.obj
        # make sure details were set
        if not hasattr(event, 'detaildata'):
            return
        # make sure something is there
        if not event.detaildata:
            return
        isIterable = lambda x : hasattr(x, '__iter__')
        for (field, value) in event.detaildata.iteritems():
                detail = proto.details.add()
                detail.name = field
                if isIterable(value):
                    for v in value:
                        detail.value.append(self.safestr(str(v)))
                else:
                    detail.value.append(self.safestr(str(value)))

    def fill(self, proto):
        """
        Sets up the event protobuf properties from the event.  If the name of
        the protobuf property is the same as the event property, then it will be
        mapped automatically assuming they are the same type.
        """
        event = self.obj

        if not proto.created_time:
            proto.created_time = int(time() * 1000)

        if hasattr(event, 'eventClass'):
            proto.event_class = self.safestr(event.eventClass)
        else:
            proto.event_class = "/Unknown"

        self.mapping.setSeverity(proto, event.severity)

        if hasattr(event, 'priority'):
            self.mapping.setPriority(proto, event.priority)

        # facility may be a string and we expect an integer
        self.coerceToInteger(event, 'facility', proto, 'syslog_facility')
        self.coerceToInteger(event, 'ntevid', proto, 'nt_event_code')

        # do our simple mappings
        for eventProperty,protoProperty in self.fieldMappings.iteritems():
            value = getattr(event, eventProperty, None)
            if value is not None:
                if isinstance(value, basestring):
                    setattr(proto, protoProperty, self.safestr(value))
                else:
                    setattr(proto, protoProperty, value)

        # copy all other event fields into details
        for field in event.getEventFields():
            if field not in self.fieldMappings:
                value = getattr(event, field)
                if isinstance(value, basestring):
                    event.detaildata[field] = self.safestr(value)
                else:
                    event.detaildata[field] = value

        self.setActor(proto)
        self.fillDetails(proto)
        return proto

