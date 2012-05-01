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

from zope.component.interfaces import Interface, IObjectEvent
from zope.interface import Attribute


# "Enum" for return values for IInvalidationFilters.
FILTER_EXCLUDE = 0
FILTER_INCLUDE = 1
FILTER_CONTINUE = 2


class IInvalidationEvent(IObjectEvent):
    """
    ZenHub has noticed an invalidation.
    """
    oid = Attribute("OID of the changed object")


class IUpdateEvent(IInvalidationEvent):
    """
    An object has been updated.
    """


class IDeletionEvent(IInvalidationEvent):
    """
    An object has been deleted.
    """


class IBatchNotifier(Interface):
    """
    Processes subdevices in batches.
    """

    def notify_subdevices(device_class, service_uid, callback):
        """
        Process subdevices of device class in batches calling callback with
        each device. The service UID uniquely identifies the service, so the
        processing of the same device_class-service pair is not duplicated.
        """


class IInvalidationProcessor(Interface):
    """
    Accepts an invalidation queue.
    """
    def processQueue(queue):
        """
        Read invalidations off a queue and deal with them. Return a Deferred
        that fires when all invalidations are done processing.
        """
    def setHub(hub):
        """
        Set the instance of ZenHub that this processor will deal with.
        """


class IServiceAddedEvent(Interface):
    """
    ZenHub has created a service.
    """
    name = Attribute("Dotted class name of the service")
    instance = Attribute("Collector name")


class IHubWillBeCreatedEvent(Interface):
    """
    A hub has been instantiated.
    """
    hub = Attribute("The hub")


class IHubCreatedEvent(Interface):
    """
    A hub has been instantiated.
    """
    hub = Attribute("The hub")


class IParserReadyForOptionsEvent(Interface):
    """
    A parser is ready for extra options to be added.
    """
    parser = Attribute("The option parser")


class IInvalidationFilter(Interface):
    """
    Filters invalidations before they're pushed to workers.
    """
    weight = Attribute("Where this filter should be in the process. Lower is earlier.")

    def initialize(context):
        """
        Initialize any state necessary for this filter to function.
        """
    def include(obj):
        """
        Return whether to exclude this device, include it absolutely, or move
        on to the next filter (L{FILTER_EXCLUDE}, L{FILTER_INCLUDE} or
        L{FILTER_CONTINUE}).
        """

class IInvalidationOid(Interface):
    """
    Allows an invalidation OID to be changed to a different OID or dropped
    """
    def tranformOid(self, oid):
        """
        Given an OID, return the same oid, a different one or None.
        """


class IHubConfProvider(Interface):
    """
    """

    def getHubConf():
        """
        """

class IHubHeartBeatCheck(Interface):
    """
    """

    def check():
        """
        """
