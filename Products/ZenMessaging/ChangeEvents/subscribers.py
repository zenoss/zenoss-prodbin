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

import logging
from zope.component import adapter
from zope.app.container.interfaces import IObjectAddedEvent,\
    IObjectRemovedEvent
from Products.ZenMessaging.queuemessaging.publisher import getModelChangePublisher
from Products.ZenMessaging.ChangeEvents.interfaces import IObjectModifiedEvent, \
    IObjectAddedToOrganizerEvent, IObjectRemovedFromOrganizerEvent, IDeviceClassMoveEvent
from Products.ZenUtils.guid.interfaces import IGloballyIdentifiable

log = logging.getLogger('zen.modelchanges')


def publishAdd(ob, event):
    publisher = getModelChangePublisher()
    publisher.publishAdd(ob)


def publishRemove(ob, event):
    publisher = getModelChangePublisher()
    publisher.publishRemove(ob)


@adapter(IGloballyIdentifiable, IObjectModifiedEvent)
def publishModified(ob, event):
    publisher = getModelChangePublisher()
    publisher.publishModified(ob)


@adapter(IGloballyIdentifiable, IObjectAddedToOrganizerEvent)
def publishAddEdge(ob, event):
    publisher = getModelChangePublisher()
    publisher.addToOrganizer(ob, event.organizer)


@adapter(IGloballyIdentifiable, IObjectRemovedFromOrganizerEvent)
def publishRemoveEdge(ob, event):
    publisher = getModelChangePublisher()
    publisher.removeFromOrganizer(ob, event.organizer)


@adapter(IGloballyIdentifiable, IDeviceClassMoveEvent)
def publishObjectMove(ob, event):
    publisher = getModelChangePublisher()
    publisher.moveObject(ob, event.fromOrganizer,
                         event.toOrganizer)
