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
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier


class ObjectProtobuf(object):
    """
    Base class for common methods on the protobuf populators
    """
    def __init__(self, obj):
        self.obj = obj

    def _getGUID(self, obj):
        return IGlobalIdentifier(obj).getGUID()

    def autoMapFields(self, proto):
        """
        This maps fields that have the same name from the
        adapted object to the protobuf
        """
        proto.guid.guid = self._getGUID(self.obj)
        fields = proto.DESCRIPTOR.fields

        # if it was modified then at least try to set every attribute
        for field in fields:
            value = getattr(self.obj, field.name, None)
            if not value:
                continue
            try:
                setattr(proto, field.name, value)
            except AttributeError:
                # likely a composite field that we will have to set manually
                continue


class DeviceProtobuf(ObjectProtobuf):
    """
    Fills up the properties of a device protobuf.
    """

    implements(IProtobufSerializer)

    def fill(self, proto):
        self.autoMapFields(proto)
        proto.ipAddress.ip = self.obj.manageIp
        # className
        deviceClass = self.obj.deviceClass()
        proto.className.guid = self._getGUID(deviceClass)
        # groups
        for group in self.obj.groups():
            groupProto = proto.groups.add()
            groupProto.guid = self._getGUID(group)

        # systems
        for system in self.obj.systems():
            systemProto = proto.systems.add()
            systemProto.guid = self._getGUID(system)

        # location
        if self.obj.location():
            proto.location.guid = self._getGuid(self.obj.location())

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

