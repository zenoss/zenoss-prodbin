##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
from zope.interface import implements, providedBy
from zope.component import adapter, getGlobalSiteManager
from twisted.internet import defer, reactor, task
from BTrees.IIBTree import IITreeSet
from ZODB.utils import u64
from Products.ZenRelations.PrimaryPathObjectManager import PrimaryPathObjectManager
from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.ZenUtils.Utils import giveTimeToReactor
from .interfaces import IInvalidationProcessor, IHubCreatedEvent
from .zodb import UpdateEvent, DeletionEvent

log = logging.getLogger('zen.ZenHub')

@defer.inlineCallbacks
def betterObjectEventNotify(event):
    """
    This method re-implements zope.component.event.objectEventNotify to give
    more time back to the reactor. It is slightly different, but works exactly
    the same for our specific use case.
    """
    gsm = getGlobalSiteManager()
    subscriptions = gsm.adapters.subscriptions(map(providedBy, (event.object, event)), None)
    for subscription in subscriptions:
        yield giveTimeToReactor(subscription, event.object, event)

def handle_oid(dmd, oid):
    # Go pull the object out of the database
    obj = dmd._p_jar[oid]
    # Don't bother with all the catalog stuff; we're depending on primaryAq
    # existing anyway, so only deal with it if it actually has primaryAq.
    if (isinstance(obj, PrimaryPathObjectManager)
          or isinstance(obj, DeviceComponent)):
        try:
            # Try to get the object
            obj = obj.__of__(dmd).primaryAq()
        except (AttributeError, KeyError), ex:
            # Object has been removed from its primary path (i.e. was
            # deleted), so make a DeletionEvent
            log.debug("Notifying services that %r has been deleted" % obj)
            event = DeletionEvent(obj, oid)
        else:
            # Object was updated, so make an UpdateEvent
            log.debug("Notifying services that %r has been updated" % obj)
            event = UpdateEvent(obj, oid)
        # Fire the event for all interested services to pick up
        return betterObjectEventNotify(event)



class InvalidationProcessor(object):
    """
    Registered as a global utility. Given a database hook and a list of oids,
    handles pushing updated objects to the appropriate services, which in turn
    cause collectors to be pushed updates.
    """
    implements(IInvalidationProcessor)

    _invalidation_queue = None
    _hub = None
    _hub_ready = None

    def __init__(self):
        self._invalidation_queue = IITreeSet()
        self._hub_ready = defer.Deferred()
        getGlobalSiteManager().registerHandler(self.onHubCreated)

    @adapter(IHubCreatedEvent)
    def onHubCreated(self, event):
        self._hub = event.hub
        self._hub_ready.callback(self._hub)

    @defer.inlineCallbacks
    def processQueue(self, oids):
        yield self._hub_ready
        i = 0
        queue = self._invalidation_queue
        if self._hub.dmd.pauseHubNotifications:
            log.debug('notifications are currently paused')
            return
        for i, oid in enumerate(oids):
            ioid = u64(oid)
            # Try pushing it into the queue, which is an IITreeSet. If it inserted
            # successfully it returns 1, else 0.
            if queue.insert(ioid):
                # Get the deferred that does the notification
                d = self._dispatch(self._hub.dmd, oid, ioid, queue)
                yield d
        defer.returnValue(i)

    def _dispatch(self, dmd, oid, ioid, queue):
        """
        Send to all the services that care by firing events.
        """
        try:
            return handle_oid(dmd, oid)
        finally:
            queue.remove(ioid)
