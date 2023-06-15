##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from enum import IntEnum
from zope.component.interfaces import Interface, IObjectEvent
from zope.interface import Attribute


class InvalidationPoller(Interface):
    """
    Manages access to object invalidations from a ZODB database storage
    object.
    """

    def poll():
        """Returns the object IDs that have changed since the last poll."""


class InvalidationFilterResult(IntEnum):
    """IInvalidationFilter implementations return one these values."""

    Exclude = 0
    Include = 1
    Continue = 2


# These names exist for backward compatibility.
FILTER_EXCLUDE = InvalidationFilterResult.Exclude
FILTER_INCLUDE = InvalidationFilterResult.Include
FILTER_CONTINUE = InvalidationFilterResult.Continue


class IInvalidationEvent(IObjectEvent):
    """ZenHub has noticed an invalidation."""

    oid = Attribute("OID of the changed object")


class IUpdateEvent(IInvalidationEvent):
    """An object has been updated."""


class IDeletionEvent(IInvalidationEvent):
    """An object has been deleted."""


class IInvalidationProcessor(Interface):
    """Accepts an invalidation queue."""

    def processQueue(queue):
        """
        Read invalidations off a queue and deal with them. Return a Deferred
        that fires when all invalidations are done processing.
        """

    def setHub(hub):
        """
        Set the instance of ZenHub that this processor will deal with.
        """


class IInvalidationFilter(Interface):
    """Filters invalidations before they're pushed to workers."""

    weight = Attribute(
        "Where this filter should be in the process. Lower is earlier.",
    )

    def initialize(context):
        """
        Initialize any state necessary for this filter to function.

        :param context: ZODB object
        """

    def include(obj):
        """
        Return whether to exclude this device, include it absolutely, or move
        on to the next filter (L{FILTER_EXCLUDE}, L{FILTER_INCLUDE} or
        L{FILTER_CONTINUE}).
        """


class IInvalidationOid(Interface):
    """
    Implementations can determine whether the updated object is a member of
    another object and return the parent object instead.  Some objects may be
    members of many objects and so multiple parents may be returned.
    """

    def transformOid(oid):
        """
        Given an OID, return the same oid, a different one,
        a list of other oids or None.
        """


__all__ = (
    "FILTER_CONTINUE",
    "FILTER_EXCLUDE",
    "FILTER_INCLUDE",
    "IDeletionEvent",
    "IInvalidationEvent",
    "IInvalidationFilter",
    "IInvalidationOid",
    "IInvalidationProcessor",
    "InvalidationFilterResult",
    "IUpdateEvent",
)
