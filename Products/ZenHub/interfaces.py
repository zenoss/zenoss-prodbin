##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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
    def tranformOid(oid):
        """
        Given an OID, return the same oid, a different one, a list of other oids or None.
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

class IWorkerSelectionAlgorithm(Interface):
    """
    Strategy class for selecting eligible zenhub workers for a given function. A default
    strategy will be created with simple selection algorithm, additional named strategies
    (named by zenhub service method) can be defined using more elaborate algorithms.
    """
    def getCandidateWorkerIds(workerlist, options):
        """
        For a given list of workers/worker state and configured options, return a 
        generator of valid worker id's. This will factor in concepts of priority and 
        allocation, to accommodate methods that are short duration and high-frequency, 
        and those of long duration and low-frequency (but may also potentially come in 
        bursts).
        """
