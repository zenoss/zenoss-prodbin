###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import logging
log = logging.getLogger('zen.ZenHub')

from zope.component.event import objectEventNotify
from zope.interface import implements
from zope.interface.advice import addClassAdvisor
from zope.component import provideHandler
from zope.component.interfaces import ObjectEvent
from ZODB.utils import u64
from twisted.internet import defer, reactor

from Products.ZenModel.Device import Device
from Products.ZenModel.DeviceComponent import DeviceComponent
from time import time
from Products.ZenRelations.PrimaryPathObjectManager import PrimaryPathObjectManager
from Products.ZenHub.interfaces import IUpdateEvent, IDeletionEvent

# time window in seconds in which we will accept changes to a device that
# will be passed on to the services
CHANGE_TIME = 300


class InvalidationEvent(ObjectEvent):
    def __init__(self, object, oid):
        super(InvalidationEvent, self).__init__(object)
        self.oid = oid


class UpdateEvent(InvalidationEvent):
    implements(IUpdateEvent)


class DeletionEvent(InvalidationEvent):
    implements(IDeletionEvent)


def _remove(_ignored, oid, queue):
    """
    We don't want bad oids hanging around forever.
    """
    queue.remove(oid)


def _dispatch(dmd, oid, ioid, queue):
    """
    Send to all the services that care by firing events.
    """
    d = defer.Deferred()
    # Closure to use as a callback
    def inner(_ignored):
        try:
            if dmd.pauseHubNotifications:
                log.debug('notifications are currently paused')
                return

            # Go pull the object out of the database
            obj = dmd._p_jar[oid]
            # Don't bother with all the catalog stuff; we're depending on primaryAq
            # existing anyway, so only deal with it if it actually has primaryAq.
            curTime = time()
            if (isinstance(obj, PrimaryPathObjectManager)
                  or isinstance(obj, DeviceComponent)):
                if (isinstance(obj, Device)
                    and obj.getLastChange().timeTime() + CHANGE_TIME < curTime):
                    log.debug('Device change for %s not within '
                                    'change window', obj.name())
                    return
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
                objectEventNotify(event)
            # Return the oid, although we don't currently use it
            return oid
        finally:
            queue.remove(ioid)
    d.addCallback(inner)
    # Call the deferred in the reactor so we give time to other things
    reactor.callLater(0, d.callback, True)
    return d


@defer.inlineCallbacks
def processInvalidations(dmd, queue, oids):
    i = 0
    for i, oid in enumerate(oids):
        ioid = u64(oid)
        # Try pushing it into the queue, which is an IITreeSet. If it inserted
        # successfully it returns 1, else 0.
        if queue.insert(ioid):
            # Get the deferred that does the notification
            d = _dispatch(dmd, oid, ioid, queue)
            yield d
    defer.returnValue(i)


def _listener_decorator_factory(eventtype):
    """
    Given a particular event interface, returns a decorator factory that may be
    used to create decorators for methods causing those methods, when bound, to
    be registered as object event subscribers.

    @param eventtype: The event interface to which the subscribers should
    listen.
    """
    def factory(*types):
        """
        The eventtype-specific decorator factory. Calling this factory both
        produces a decorator and wraps the __init__ of the class of the
        decorated method with a function that registers the handlers.
        """
        # Create a mutable to store the handler name between the call to
        # decorator and the call to advisor (simple assignment won't work for
        # scope reasons)
        _f = {}

        def decorator(f):
            """
            The decorator. All it does is print a log message, then call the
            original function.
            """
            def inner(self, obj, event):
                # Log that we've called this listener
                fname = '.'.join((self.__class__.__name__, f.__name__))
                log.debug('%s is interested in %r for %r' % (fname, event, obj))

                # Call the original function
                return f(self, obj, event)

            # Push the name of the function outside the decorator scope so the
            # class advisor has access when it needs to register handlers.
            _f[f.__name__] = 1

            # Return the closure to replace the original function.
            return inner

        def advisor(cls):
            """
            A class advisor that is called after the class is created. We use
            this to wrap __init__ in a function that registers any handlers
            created via this factory, which are stored on the class.
            """
            # Set one flag per fname on the class so we don't double-register
            # when we override in a subclass (once for super, once for sub)
            fname = _f.keys()[0]
            cls.__registered = getattr(cls, '__registered', {})

            # Check our flag
            if fname not in cls.__registered:
                # Decorator for __init__
                def registerHandlers(f):
                    def __init__(self, *args, **kwargs):
                        # Call the original constructor; we'll register handlers
                        # afterwards
                        f(self, *args, **kwargs)
                        handler = getattr(self, fname)
                        for t in types:
                            # Register the handler. Here's where we use
                            # eventtype, which was passed in to the outermost
                            # function in this behemoth.
                            provideHandler(handler, (t, eventtype))

                    # Return the closure to replace the decorated method
                    return __init__

                # Decorate __init__ so it will register the handlers on
                # instantiation
                cls.__init__ = registerHandlers(cls.__init__)
                # Set the flag for this fname
                cls.__registered[fname] = 1

            # Return the class, which will replace the original class.
            return cls

        # Add the advisor to the class.
        addClassAdvisor(advisor)

        # Return the decorator so we get the log message when called
        return decorator

    return factory


# Create two decorator factories for the two kinds of events.
onUpdate = _listener_decorator_factory(IUpdateEvent)
onDelete = _listener_decorator_factory(IDeletionEvent)
