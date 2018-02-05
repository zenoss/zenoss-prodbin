##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from zope.event import notify
from zope.interface import implementer
from zope.component import adapter, getUtility
from zope.container.interfaces import IObjectAddedEvent, IObjectMovedEvent
from zope.container.interfaces import IObjectRemovedEvent
from OFS.interfaces import IObjectWillBeMovedEvent, IObjectWillBeAddedEvent
from interfaces import (
    IIndexingEvent, IAfterIndexingEventSubscriber, IGloballyIndexed,
    ITreeSpanningComponent, IDeviceOrganizer
)

from Products.Zuul.catalog.interfaces import IModelCatalog
from Products.Zuul.catalog.exceptions import BadIndexingEvent


@implementer(IIndexingEvent)
class IndexingEvent(object):
    def __init__(
            self, object,
            idxs=None, update_metadata=True, triggered_by_zope_event=False):
        """
        @param triggered_by_zope_event : flag to indicate whether the
            IndexingEvent was triggered by zope events
            (IObjectWillBeMovedEvent, IObjectAddedEvent etc) or not.
        """
        self.object = object
        self.idxs = idxs
        self.update_metadata = update_metadata
        self.triggered_by_zope_event = triggered_by_zope_event
        self.triggered_by_maint_window = False


def _get_object_to_index(ob):
    """
    Returns the object to be indexed/unindexed or None
    if the object does not have to be indexed
    """
    try:
        evob = ob.primaryAq()
    except (AttributeError, KeyError):
        evob = ob
    path = evob.getPrimaryPath()
    # Ignore things dmd or above
    return evob if (len(path) > 3 and path[2] == "dmd") else None


@adapter(IGloballyIndexed, IIndexingEvent)
def onIndexingEvent(ob, event):

    object_to_index = _get_object_to_index(ob)
    if not object_to_index:
        return

    idxs = event.idxs
    if isinstance(idxs, basestring):
        idxs = [idxs]

    model_catalog = getUtility(IModelCatalog)

    if idxs:
        s_idxs = set(idxs)
        indexed, stored, _ = model_catalog.get_indexes(object_to_index)
        obj_indexes = indexed.union(stored)
        # Every time "path" is indexed, also index "deviceOrganizers"
        if "path" in s_idxs and "deviceOrganizers" in obj_indexes:
            s_idxs.add("deviceOrganizers")
            idxs = s_idxs
        # check idxs are valid indexes
        bad_idxs = s_idxs - obj_indexes
        if bad_idxs:
            raise BadIndexingEvent(
                "Indexing event contains unknown indexes: %s" % (bad_idxs,)
            )

    model_catalog.catalog_object(object_to_index, idxs)
    if IAfterIndexingEventSubscriber.providedBy(object_to_index):
        object_to_index.after_indexing_event(event)


@adapter(IGloballyIndexed, IObjectWillBeMovedEvent)
def onObjectRemoved(ob, event):
    """
    Unindex, please.
    """
    if not IObjectWillBeAddedEvent.providedBy(event):
        object_to_unindex = _get_object_to_index(ob)
        if object_to_unindex:
            getUtility(IModelCatalog).uncatalog_object(object_to_unindex)


@adapter(IGloballyIndexed, IObjectAddedEvent)
def onObjectAdded(ob, event):
    """
    Simple subscriber that fires the indexing event for all
    indices.
    """
    notify(IndexingEvent(ob, triggered_by_zope_event=True))


@adapter(IGloballyIndexed, IObjectMovedEvent)
def onObjectMoved(ob, event):
    """
    Reindex paths only
    """
    if not (IObjectAddedEvent.providedBy(event) or
            IObjectRemovedEvent.providedBy(event)):
        notify(IndexingEvent(ob, idxs='path', triggered_by_zope_event=True))


@adapter(IDeviceOrganizer, IObjectWillBeMovedEvent)
def onOrganizerBeforeDelete(ob, event):
    """
    Before we delete the organizer we need to remove its references
    to the devices.
    """
    if not IObjectWillBeAddedEvent.providedBy(event):
        for device in ob.devices.objectValuesGen():
            notify(IndexingEvent(
                device, idxs='path', triggered_by_zope_event=True
            ))


# -------------------------------------------------------------
#    Methods to deal with tree spanning components.
#    When a tree spanning component is updated, we need
#    to make sure that the object the component is linked
#    to in the other tree is updated if needed
# -------------------------------------------------------------


class ObjectsAffectedBySpanningComponent(object):

    def __init__(self, component):
        self.component = component
        self.peers = self._set_component_peers(component)

    def _set_component_peers(self, component):
        peers = []
        if hasattr(component, "get_indexable_peers"):
            peers = component.get_indexable_peers()
            if not hasattr(peers, '__iter__'):
                peers = [peers]
        return peers

    def index_affected_objects(self):
        for peer in self.peers:
            notify(IndexingEvent(peer, triggered_by_zope_event=True))


@adapter(ITreeSpanningComponent, IObjectWillBeMovedEvent)
def onTreeSpanningComponentBeforeDelete(ob, event):
    """ Before tree spanning component is deleted """
    if not IObjectWillBeAddedEvent.providedBy(event):
        affected_objects = ObjectsAffectedBySpanningComponent(ob)
        affected_objects.index_affected_objects()


@adapter(ITreeSpanningComponent, IObjectMovedEvent)
def onTreeSpanningComponentAfterAddOrMove(ob, event):
    """ When tree spanning component is added or moved """
    if not IObjectRemovedEvent.providedBy(event):
        affected_objects = ObjectsAffectedBySpanningComponent(ob)
        affected_objects.index_affected_objects()
