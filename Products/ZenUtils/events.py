##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################
from contextlib import contextmanager
from collections import defaultdict

from zope.interface import implements, Interface, Attribute
from zope.event import notify
from zope.component import getGlobalSiteManager
from zope.component import provideHandler
from ZODB.transact import transact

from Products.PluggableAuthService.interfaces.events import IUserLoggedInEvent
from Products.PluggableAuthService.interfaces.events import IUserLoggedOutEvent
from Products.PluggableAuthService.events import PASEvent

GSM = getGlobalSiteManager()

class UserLoggedInEvent(PASEvent):
    """
    Login notification event.

    Subscribe to this to run code when a user logs in.
    The username can be obtained in the handler via: evt.object.id

    WARNING: Currently it doesn't notify when switching directly from
             a non-admin user to the admin user without logging out,
             because we're unable to determine whether the login succeeded.
    """
    implements(IUserLoggedInEvent)


class UserLoggedOutEvent(PASEvent):
    """
    Manual logout notification event.

    This does not fire for session timeouts.
    """
    implements(IUserLoggedOutEvent)

class IZopeApplicationOpenedEvent(Interface):
    """
    Returns the Zope application.
    """
    app = Attribute("The Zope Application")

class ZopeApplicationOpenedEvent(object):
    implements(IZopeApplicationOpenedEvent)

    def __init__(self, app):
        self.app = app

def notifyZopeApplicationOpenedSubscribers(event):
    """
    Re-fires the IDatabaseOpenedWithRoot notification to subscribers with an
    open handle to the application defined in the database.
    """
    db = event.database
    conn = db.open()
    try:
        app = conn.root()['Application']
        transact(notify)(ZopeApplicationOpenedEvent(app))
    finally:
        conn.close()


def pauseHandler(handler, buffer=None):
    if buffer is None:
        buffer = []

    handlers = []

    for reg in GSM.registeredHandlers():
        if reg.handler == handler:
            required = reg.required
            
            def tempHandler(*args, **kwargs):
                buffer.append((args, kwargs))

            provideHandler(tempHandler, required)
            handlers.append((tempHandler, required))

            GSM.unregisterHandler(handler, required=required)  

    return buffer, handlers


def unpauseHandler(handler, buffer=None, temp_handlers=None):
    if temp_handlers is not None:
        for temp_handler, required in temp_handlers:
            GSM.unregisterHandler(temp_handler, required=required)
            provideHandler(handler, required)

    if buffer is not None:
        for args, kwargs in buffer:
            handler(*args, **kwargs)


@contextmanager
def paused(handler, buffer=None):
    buffer, temp_handlers = pauseHandler(handler, buffer)
    yield 
    unpauseHandler(handler, buffer, temp_handlers)
     

class OptimizedIndexingBuffer(object):
    """
    Accumulates and dedupes IndexingEvents so that only one will eventually be
    fired per object.
    """
    def __init__(self):
        self.removed_buffer = []
        self.indexes = defaultdict(set)
        self.update_metadatas = {}
        self.args = {}
        from Products.Zuul.catalog.events import IndexingEvent
        self.IndexingEvent = IndexingEvent
    
    def append(self, (args, kwargs)):
        ob, event = args
        if not isinstance(event, self.IndexingEvent):
            # Removal event; just delete what's there
            self.indexes.pop(ob, None)
            self.update_metadatas.pop(ob, None)
            self.removed_buffer.append((args, kwargs))
        else:
            # If indexes are specified, we have decisions to make
            if event.idxs:
                idxs = ((event.idxs,) if isinstance(event.idxs, basestring) 
                        else event.idxs)
                # Have we seen the ob already? If not, add the indexes
                # If we have seen it already, only update if the set isn't 
                # empty, which signifies all indexes (thereby encompassing
                # those specified in the event)
                if ob not in self.indexes or self.indexes[ob]:
                    self.indexes[ob].update(idxs)
            else:
                # Replace whatever's there with an empty set
                self.indexes[ob] = set()

            # Update metadata if any event says to do so
            self.update_metadatas[ob] = (self.update_metadatas.get(ob, False) 
                                         or event.update_metadata)

    def __iter__(self):
        for ob, idxs in self.indexes.iteritems():
            yield ((ob, self.IndexingEvent(ob, tuple(self.indexes.get(ob, ())), 
                        self.update_metadatas.get(ob, False))), {})


class UnindexingBuffer(object):
    def __init__(self, wrapped_buffer):
        self.wrapped_buffer = wrapped_buffer

    def append(self, *args, **kwargs):
        self.wrapped_buffer.append(*args, **kwargs)

    def __iter__(self):
        return iter(self.wrapped_buffer.removed_buffer)


@contextmanager
def pausedAndOptimizedIndexing(index_handler=None, unindex_handler=None):
    """
    Delay global catalog indexing for the duration of the with block. Also,
    collapse indexing events so that only one is fired per object.
    """
    # Circular import
    from Products.Zuul.catalog.events import onIndexingEvent
    index_handler = index_handler or onIndexingEvent

    # Circular import
    from Products.Zuul.catalog.events import onObjectRemoved
    unindex_handler = unindex_handler or onObjectRemoved

    index_buffer = OptimizedIndexingBuffer()
    with paused(index_handler, index_buffer):
        with paused(unindex_handler, UnindexingBuffer(index_buffer)):
            yield

