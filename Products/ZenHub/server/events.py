##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from zope.interface import implementer

from ..interfaces import IServiceAddedEvent
from .interface import (
    IServiceCallReceivedEvent,
    IServiceCallStartedEvent,
    IServiceCallCompletedEvent,
)
from .utils import UNSPECIFIED as _UNSPECIFIED


@implementer(IServiceAddedEvent)
class ServiceAddedEvent(object):
    """An event class dispatched when a service is first loaded."""

    def __init__(self, name, instance):
        """Initialize a ServiceAddedEvent instance.

        @param name {str} Name of the service.
        @param instance {str} Name of the performance monitor (collector).
        """
        self.name = name
        self.instance = instance


class ReportWorkerStatus(object):
    """An event to signal zenhubworkers to report their status."""


class ServiceCallEvent(object):
    """Base class for ServiceCall* event classes."""

    __slots__ = ()

    def __init__(self, **kwargs):
        for name in self.__slots__:
            setattr(self, name, kwargs.pop(name, None))
        # no left-over arguments
        assert len(kwargs) == 0, ("[%r] invalid arguments" % self)
        super(ServiceCallEvent, self).__init__()


@implementer(IServiceCallReceivedEvent)
class ServiceCallReceived(ServiceCallEvent):
    """ZenHub has accepted a request to execute a method on a service."""

    __slots__ = (
        "id", "monitor", "service", "method", "args", "kwargs",
        "timestamp", "queue", "priority",
    )


@implementer(IServiceCallStartedEvent)
class ServiceCallStarted(ServiceCallEvent):
    """ZenHub has started executing a method on a service."""

    __slots__ = ServiceCallReceived.__slots__ + ("worker", "attempts")

    def __init__(self, **kwargs):
        assert kwargs.get("attempts") is not None, "attempts is unspecified"
        assert kwargs["attempts"] > 0, "attempts is less than 1"
        super(ServiceCallStarted, self).__init__(**kwargs)


@implementer(IServiceCallCompletedEvent)
class ServiceCallCompleted(ServiceCallEvent):
    """ZenHub has completed executing a method on a service."""

    __slots__ = ServiceCallStarted.__slots__ + ("retry", "error", "result")

    def __init__(self, **kwargs):
        assert kwargs.get("attempts") is not None, "attempts is unspecified"
        assert kwargs["attempts"] > 0, "attempts is less than 1"
        error = kwargs.get("error", _UNSPECIFIED)
        retry = kwargs.get("retry", _UNSPECIFIED)
        result = kwargs.get("result", _UNSPECIFIED)
        assert any((
            all((
                (result is not _UNSPECIFIED),
                (error is _UNSPECIFIED),
                (retry is _UNSPECIFIED),
            )),
            all((
                (result is _UNSPECIFIED),
                (error is not _UNSPECIFIED),
                (retry is _UNSPECIFIED),
            )),
            all((
                (result is _UNSPECIFIED),
                (error is _UNSPECIFIED),
                (retry is not _UNSPECIFIED),
            )),
        )), "[completed] Fields result, retry, and error all unspecified"
        super(ServiceCallCompleted, self).__init__(**kwargs)
