##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
from zope.component import adapter
from zope.container.interfaces import IObjectAddedEvent,\
    IObjectRemovedEvent
from Products.ZenMessaging.queuemessaging.publisher import getModelChangePublisher
from Products.Zuul.catalog.interfaces import IIndexingEvent
from Products.ZenMessaging.ChangeEvents.interfaces import \
    IObjectAddedToOrganizerEvent, IObjectRemovedFromOrganizerEvent, IDeviceClassMoveEvent
from Products.ZenUtils.guid.interfaces import IGloballyIdentifiable

log = logging.getLogger('zen.modelchanges')


def publishAdd(ob, event):
    publisher = getModelChangePublisher()
    publisher.publishAdd(ob)


def publishRemove(ob, event):
    publisher = getModelChangePublisher()
    publisher.publishRemove(ob)


@adapter(IGloballyIdentifiable, IIndexingEvent)
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
