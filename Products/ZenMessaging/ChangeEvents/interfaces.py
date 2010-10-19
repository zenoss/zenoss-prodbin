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

from zope.interface import Attribute
from zope.component.interfaces import IObjectEvent


class IObjectModifiedEvent(IObjectEvent):
    """
    An event that is fired when an object is modified. This doesn't say what
    changed, just notifies that a property of the object changed. It is up to
    the subscriber to determine what changed
    """


class IObjectAddedToOrganizerEvent(IObjectEvent):
    """
    An event that is fired when an object is added to an organizer. For instance
    Groups, System, Locations and Dynamic Services
    """
    organizer = Attribute("Organizer the object is added to")


class IObjectRemovedFromOrganizerEvent(IObjectEvent):
    """
    An event that is fired when an object is removed from an organizer
    """
    organizer = Attribute("Organizer the object is removed from")


class IDeviceClassMoveEvent(IObjectEvent):
    """
    An event that is fired when an object is removed from an organizer
    """
    fromOrganizer = Attribute("Organizer the object is moved from")
    toOrganizer =  Attribute("Organizer the object is moved to")

