##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import implements
from Products.ZenMessaging.ChangeEvents.interfaces import \
    IObjectAddedToOrganizerEvent, IObjectRemovedFromOrganizerEvent, \
    IDeviceClassMoveEvent, IMessagePrePublishingEvent
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer

import logging
log = logging.getLogger('zen.modelchanges')


class ObjectAddedToOrganizerEvent(object):
    """
    When an object is added to a new organizer
    """
    implements(IObjectAddedToOrganizerEvent)
    def __init__(self, object, organizer):
        self.object = object
        if not isinstance(organizer, DeviceOrganizer):
            raise TypeError(" %s is not an instance of Device Organizer" % organizer)
        self.organizer = organizer


class ObjectRemovedFromOrganizerEvent(object):
    """
    When an object is removed from an organizer
    """
    implements(IObjectRemovedFromOrganizerEvent)
    def __init__(self, object, organizer):
        self.object = object
        if not isinstance(organizer, DeviceOrganizer):
            raise TypeError(" %s is not an instance of Device Organizer" % organizer)
        self.organizer = organizer


class DeviceClassMovedEvent(object):
    """
    Fired when a device moves from a class to another
    """
    implements(IDeviceClassMoveEvent)

    def __init__(self, object, fromOrganizer, toOrganizer):
        self.object = object
        self.fromOrganizer = fromOrganizer
        self.toOrganizer = toOrganizer


class MessagePrePublishingEvent(object):
    """
    Fired just before a batch of ModelChangeList messages is published to
    Rabbit.
    """
    implements(IMessagePrePublishingEvent)
    def __init__(self, msgs):
        self.msgs = msgs

