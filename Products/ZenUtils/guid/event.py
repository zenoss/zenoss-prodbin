##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
from zope.event import notify
from zope.component import adapter
from zope.interface import implements
from zope.component.interfaces import ObjectEvent
from zope.container.interfaces import IObjectMovedEvent, IObjectRemovedEvent
from OFS.interfaces import IObjectWillBeMovedEvent, IObjectWillBeAddedEvent
from .interfaces import IGUIDEvent, IGUIDManager, IGloballyIdentifiable
from .interfaces import IGlobalIdentifier

log = logging.getLogger('zen.UUID')


class GUIDEvent(ObjectEvent):
    implements(IGUIDEvent)
    def __init__(self, object, old, new, update_global_catalog=True):
        super(GUIDEvent, self).__init__(object)
        self.old = old
        self.new = new
        self.update_global_catalog = update_global_catalog


@adapter(IGloballyIdentifiable, IGUIDEvent)
def registerGUIDToPathMapping(object, event):
    mgr = IGUIDManager(object)
    if event.new:
        mgr.setObject(event.new, object)
        if event.update_global_catalog:
            try:
                catalog = object.global_catalog
                catalog.catalog_object(object, idxs=(), update_metadata=True)
            except Exception:
                log.exception('Encountered a guid exception')
    if event.old and event.old != event.new:
        # When we move a component around,
        # we don't want to remove the guid
        # from the catalog
        if mgr.getPath(event.old) == object.getPrimaryUrlPath():
            mgr.remove(event.old)


@adapter(IGloballyIdentifiable, IObjectMovedEvent)
def refireEventOnObjectAddOrMove(object, event):
    if not IObjectRemovedEvent.providedBy(event):
        oldguid = IGlobalIdentifier(object).getGUID()
        if oldguid is None:
            IGlobalIdentifier(object).create()
        else:
            # Refire in the case where an object already has a guid
            # but that guid has been removed from the guid table
            notify(GUIDEvent(object, oldguid, oldguid, False))


@adapter(IGloballyIdentifiable, IObjectWillBeMovedEvent)
def refireEventOnObjectBeforeRemove(object, event):
    if not IObjectWillBeAddedEvent.providedBy(event):
        guid = IGlobalIdentifier(object).guid
        notify(GUIDEvent(object, guid, None))
