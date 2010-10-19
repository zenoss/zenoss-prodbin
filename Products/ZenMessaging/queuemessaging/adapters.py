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


class ProtobufMappings:
    """
    Handles the mapping between zenoss constants
    and protobuf constants
    """
    event_statuses = {
        '0': 'STATUS_NEW',
        '1': 'STATUS_ACKNOWLEDGED',
        '2': 'STATUS_SUPPRESSED'}

    priorities = {
        '-1': 'PRIORITY_NONE',
        '0': 'PRIORITY_EMERGENCY',
        '1': 'PRIORITY_ALERT',
        '2': 'PRIORITY_CRITICAL',
        '3': 'PRIORITY_ERROR',
        '4': 'PRIORITY_WARNING',
        '6': 'PRIORITY_NOTICE'}

    severities = {
        '0': 'SEVERITY_CLEAR',
        '1': 'SEVERITY_DEBUG',
        '2': 'SEVERITY_INFO',
        '3': 'SEVERITY_WARNING',
        '4': 'SEVERITY_ERROR',
        '5': 'SEVERITY_CRITICAL'}

    def _setMapping(self, proto, field,  constant, mapping):
        """
        Checks to make sure we are sending a correct value and then
        updates the protobuf with the correct attribute.
        NOTE: enums are attributes on the object. For instance,
              To get the PRIORITY_NONE enum value you would call:
               - eventProtobuf.PRIORITY_NONE
               where eventProtobuf is an instance of the Event Protobuf Class
        """
        # it is possible it was set to None
        if not str(constant):
            return
        if not str(constant) in mapping.keys():
            raise AssertionError("%s is not a valid value of %s " % (constant, mapping))
        value = getattr(proto, mapping[str(constant)])
        setattr(proto, field, value)

    def setSeverity(self, proto, zenossSeverityConstant):
        """
        Assumes the constant to be one of our severity mappings
        @type  proto: Protobuf
        @param proto: Protobuf we want the severity set on
        @type  zenossSeverityConstant: int
        @param zenossSeverityConstant:
        """
        self._setMapping(proto, 'severity', zenossSeverityConstant, self.severities)

    def setPriority(self, proto, zenossPriorityConstant):
        """
        Assumes the constant to be one of our priority mappings
        @type  proto: Protobuf
        @param proto: Protobuf we want the priority set on
        @type  zenossPriorityConstant: int
        @param zenossPriorityConstant:
        """
        self._setMapping(proto, 'priority', zenossPriorityConstant, self.priorities)

    def setEventStatus(self, proto, zenossStatusConstant):
        """
        Assumes the constant to be one of our status mappings
        @type  proto: Protobuf
        @param proto: Protobuf we want the status set on
        @type  zenossStatusConstant: int
        @param zenossStatusConstant:
        """
        self._setMapping(proto, 'status', zenossStatusConstant, self.event_statuses)


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

    implements(IProtobufSerializer)

    def fill(self, proto):
        self.autoMapFields(proto)
        proto.ip_address = self.obj.manageIp
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

    implements(IProtobufSerializer)

    def fill(self, proto):
        self.autoMapFields(proto)
        return proto


class DeviceComponentProtobuf(ObjectProtobuf):
    """
    Fills up the properties of a Device Component
    """
    implements(IProtobufSerializer)

    def fill(self, proto):
        self.autoMapFields(proto)
        # use device protobuf to fill out our device property
        device = self.obj.device()
        populator = DeviceProtobuf(device)
        populator.fill(proto.device)
        return proto


class EventProtobuf(ObjectProtobuf):
    """
    Fills up the properties of an event
    """

    detailFields = ('stateChange', 'suppid', 'ntevid')

    def __init__(self, obj, dmd=False):
        ObjectProtobuf.__init__(self, obj)
        self.mapping = ProtobufMappings()

    def _lookupActor(self, event,  actorId, type):
        """
        This returns the zope object for the actor
        that we are looking at specifically for this event
        """
        if type == "device":
            return self.dmd.Devices.findDevice(actorId)
        if type == "component":
            device = self.dmd.Devices.findDevice(event.device)
            if device:
                for component in device.getDeviceComponents():
                    if component.id == actorId:
                        return component

    def setActor(self, proto):
        """
        This sets the "actor" attribute of the event.
        Can be any combination of device/component/service (including
        all three).
        """
        # type is defaulted to 1 need to know if I set it or not
        event = self.obj
        for type in ('component', 'device', 'service'):
            if hasattr(event, type):
                # device doesn't exist in our database, just id it
                actorName = getattr(event, type)
                # set type
                obj = self._lookupActor(event, getattr(event, type), type)
                subproto = getattr(proto.actor, type)
                if obj:
                    # fill out all the properties we can
                    populator = IProtobufSerializer(obj)
                    populator.fill(subproto)
                elif actorName:
                     # it doesn't exist in our database (yet)
                    subproto.id = actorName

    def fillDetails(self, proto):
        """
        These are just extra fields on the event. The specific
        fields are defined in "self.detailFields"
        """
        event = self.obj
        for field in self.detailFields:
            if hasattr(event, field):
                value = getattr(event, field)
                if not value:
                    continue
                detail = proto.details.add()
                detail.name = field
                detail.value.append(value)

    def fill(self, proto, dmd):
        """
        Sets up the event protobuf properties from the event.  If the name of
        the protobuf property is the same as the event property, then it will be
        mapped automatically assuming they are the same type.
        """
        self.dmd = dmd
        event = self.obj
        # evid must be set at this point
        proto.uuid = event.evid
        if hasattr(event, 'eventClass'):
            proto.event_class.className = event.eventClass
        else:
            proto.event_class.className = "/Unknown"
        self.autoMapFields(proto)
        proto.event_class.key = event.eventKey
        proto.created_time = int(event.firstTime)
        proto.first_seen_time = int(event.firstTime)
        proto.last_seen_time = int(event.lastTime)
        self.mapping.setSeverity(proto, event.severity)
        if hasattr(event, 'priority'):
            self.mapping.setPriority(proto, event.priority)
        if hasattr(event, 'eventState'):
            self.mapping.setEventStatus(proto, event.eventState)
        if hasattr(event, 'eventKey'):
            proto.event_key = event.eventKey
        if hasattr(event, 'ipAddress'):
            proto.ip_address = event.ipAddress
        if hasattr(event, 'ownerid'):
            proto.owner_id = event.ownerid

        self.setActor(proto)
        self.fillDetails(proto)
        return proto
