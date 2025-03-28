##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.component.interfaces import Interface, IObjectEvent
from zope.interface import Attribute


class IObjectAddedToOrganizerEvent(IObjectEvent):
    """
    Fired when an object is added to an organizer.
    For instance Groups, System, Locations and Dynamic Services.
    """

    organizer = Attribute("Organizer the object is added to")


class IObjectRemovedFromOrganizerEvent(IObjectEvent):
    """Fired when an object is removed from an organizer."""

    organizer = Attribute("Organizer the object is removed from")


class IDeviceClassMoveEvent(IObjectEvent):
    """Fired when an object is removed from an organizer."""

    fromOrganizer = Attribute("Organizer the object is moved from")
    toOrganizer = Attribute("Organizer the object is moved to")


class IMessagePrePublishingEvent(Interface):
    """
    Fired just before a batch of ModelChangeList messages is published to
    Rabbit.
    """

    msgs = Attribute("list of ModelChanges")


class IMessagePostPublishingEvent(Interface):
    """Fired after transaction completion."""

    msgs = Attribute("list of ModelChanges")
