##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.component.interfaces import Interface
from zope.interface import Attribute

# Import invalidation related names for compatibility with ZenPacks.
from .modelchange.interfaces import *  # noqa E403


class IBatchNotifier(Interface):
    """Processes subdevices in batches."""

    def notify_subdevices(device_class, service_uid, callback):
        """
        Process subdevices of device class in batches calling callback with
        each device. The service UID uniquely identifies the service, so the
        processing of the same device_class-service pair is not duplicated.
        """


class IServiceAddedEvent(Interface):
    """ZenHub has created a service."""

    name = Attribute("Dotted class name of the service")
    instance = Attribute("Collector name")


class IHubWillBeCreatedEvent(Interface):
    """A hub has been instantiated."""

    hub = Attribute("The hub")


class IHubCreatedEvent(Interface):
    """A hub has been instantiated."""

    hub = Attribute("The hub")


class IParserReadyForOptionsEvent(Interface):
    """A parser is ready for extra options to be added."""

    parser = Attribute("The option parser")


class IHubConfProvider(Interface):
    """"""

    def getHubConf():
        """"""


class IHubHeartBeatCheck(Interface):
    """"""

    def check():
        """"""


class ICollectorEventFingerprintGenerator(Interface):
    """
    Interface used to generate a fingerprint for an event on the collector.
    Event fingerprints are used on the collector to perform de-duplication
    of events. Events are de-duplicated to prevent event floods of
    similar/identical events from overwhelming the system.

    The default fingerprint generator (if no additional ones are implemented)
    is a pipe-delimited string consisting of the following:

     - eventKey specified: device, component, eventClass, eventKey, severity
     - no eventKey: device, component, eventClass, severity, summary

    This matches the default algorithm used in zeneventd to
    de-duplicate events.

    NOTE: This fingerprint is not persisted in any way on the event - it is
    only used to perform de-duplication at the collector before events are
    flushed to ZenHub.
    """

    weight = Attribute(
        "The priority of the fingerprint generator. Generators are executed "
        "in ascending order until the first non-None fingerprint is returned",
    )

    def generate(event):
        """
        Generates a fingerprint for the event, or returns None if this
        generator should not be used to generate a fingerprint for this event
        (the next generator, if found, will be run).

        @param event: The event to generate a fingerprint for.
        @type event: dict
        @return: A fingerprint for the event (string) used for de-duplication
            of events at the collector. If this generator cannot generate a
            fingerprint for the event, then it should return None.
        @rtype: str
        """


TRANSFORM_CONTINUE = 0
TRANSFORM_STOP = 1
TRANSFORM_DROP = 2


class ICollectorEventTransformer(Interface):
    """
    Interface used to perform filtering of events at the collector.
    This could be used to drop events, transform event content, etc.

    These transformers are run sequentially before a fingerprint is generated
    for the event, so they can set fields which are used by an
    ICollectorEventFingerprintGenerator.
    """

    weight = Attribute(
        "The priority of the event transformer (the transformers are "
        "executed in ascending order using the weight of each filter)",
    )

    def transform(event):
        """
        Performs any transforms of the specified event at the collector.

        @param event: The event to transform.
        @type event: dict
        @return: Returns TRANSFORM_CONTINUE if this event should be forwarded
            on to the next transformer in the sequence, TRANSFORM_STOP if no
            further transformers should be performed on this event, and
            TRANSFORM_DROP if the event should be dropped.
        @rtype: int
        """
