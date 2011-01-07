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
from zope.event import notify
from zope.component import adapter
from zope.interface import implements
from zope.component.interfaces import ObjectEvent
from zope.app.container.interfaces import IObjectMovedEvent, IObjectRemovedEvent
from OFS.interfaces import IObjectWillBeMovedEvent, IObjectWillBeAddedEvent
from .interfaces import IGUIDEvent, IGUIDManager, IGloballyIdentifiable
from .interfaces import IGlobalIdentifier


class GUIDEvent(ObjectEvent):
    implements(IGUIDEvent)
    def __init__(self, object, old, new):
        super(GUIDEvent, self).__init__(object)
        self.old = old
        self.new = new


@adapter(IGloballyIdentifiable, IGUIDEvent)
def registerGUIDToPathMapping(object, event):
    mgr = IGUIDManager(object)
    if event.new:
        mgr.setObject(event.new, object)
        try:
            catalog = object.global_catalog
            catalog.catalog_object(object, idxs=(), update_metadata=True)
        except Exception:
            pass
    if event.old and event.old != event.new:
        # When we move a component around,
        # we don't want to remove the guid
        # from the catalog
        if mgr.getPath(event.old) == object.getPrimaryUrlPath():
            mgr.remove(event.old)


@adapter(IGloballyIdentifiable, IObjectMovedEvent)
def refireEventOnObjectAddOrMove(object, event):
    if not IObjectRemovedEvent.providedBy(event):
        IGlobalIdentifier(object).create()


@adapter(IGloballyIdentifiable, IObjectWillBeMovedEvent)
def refireEventOnObjectBeforeRemove(object, event):
    if not IObjectWillBeAddedEvent.providedBy(event):
        guid = IGlobalIdentifier(object).guid
        notify(GUIDEvent(object, guid, None))
