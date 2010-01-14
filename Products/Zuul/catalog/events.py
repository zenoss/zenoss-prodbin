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

from zope.event import notify
from zope.interface import implements
from zope.component import adapter
from zope.app.container.interfaces import IObjectAddedEvent, IObjectMovedEvent
from zope.app.container.interfaces import IObjectRemovedEvent
from OFS.interfaces import IObjectWillBeMovedEvent, IObjectWillBeAddedEvent
from interfaces import IIndexingEvent, IGloballyIndexed, ITreeSpanningComponent
from paths import devicePathsFromComponent

class IndexingEvent(object):
    implements(IIndexingEvent)
    def __init__(self, object, idxs=None, update_metadata=True):
        self.object = object
        self.idxs = idxs
        self.update_metadata = update_metadata


@adapter(IGloballyIndexed, IIndexingEvent)
def onIndexingEvent(ob, event):
    try:
        catalog = ob.getPhysicalRoot().zport.global_catalog
    except (KeyError, AttributeError):
        # Migrate script hasn't run yet; ignore indexing
        return
    idxs = event.idxs
    if isinstance(idxs, basestring):
        idxs = [idxs]
    catalog.catalog_object(event.object.primaryAq(), idxs=idxs, 
                           update_metadata=event.update_metadata)


@adapter(IGloballyIndexed, IObjectWillBeMovedEvent)
def onObjectRemoved(ob, event):
    """
    Unindex, please.
    """
    if not IObjectWillBeAddedEvent.providedBy(event):
        try:
            catalog = ob.getPhysicalRoot().zport.global_catalog
        except (KeyError, AttributeError):
            # Migrate script hasn't run yet; ignore indexing
            return
        uid = '/'.join(ob.getPrimaryPath())
        catalog.uncatalog_object(uid)


@adapter(IGloballyIndexed, IObjectAddedEvent)
def onObjectAdded(ob, event):
    """
    Simple subscriber that fires the indexing event for all
    indices.
    """
    notify(IndexingEvent(ob))


@adapter(IGloballyIndexed, IObjectMovedEvent)
def onObjectMoved(ob, event):
    """
    Reindex paths only, don't update metadata.
    """
    if not (IObjectAddedEvent.providedBy(event) or
            IObjectRemovedEvent.providedBy(event)):
        notify(IndexingEvent(ob, 'path', False))


@adapter(ITreeSpanningComponent, IObjectWillBeMovedEvent)
def onTreeSpanningComponentBeforeDelete(ob, event):
    """
    When a component that links a device to another tree is going to
    be removed, update the device's paths.
    """
    if not IObjectWillBeAddedEvent.providedBy(event):
        component = ob
        try:
            catalog = ob.getPhysicalRoot().zport.global_catalog
        except (KeyError, AttributeError):
            # Migrate script hasn't run yet; ignore indexing
            return
        device = component.device()
        if not device:
            # OS relation has already been broken; get by path
            devpath = component.getPrimaryPath()[:-3]
            device = component.unrestrictedTraverse(devpath)
        if device:
            oldpaths = devicePathsFromComponent(component)
            catalog.unindex_object_from_paths(device, oldpaths)


@adapter(ITreeSpanningComponent, IObjectMovedEvent)
def onTreeSpanningComponentAfterAddOrMove(ob, event):
    if not IObjectRemovedEvent.providedBy(event):
        component = ob
        try:
            catalog = ob.getPhysicalRoot().zport.global_catalog
        except (KeyError, AttributeError):
            # Migrate script hasn't run yet; ignore indexing
            return
        device = component.device()
        newpaths = devicePathsFromComponent(component)
        catalog.index_object_under_paths(device, newpaths)
