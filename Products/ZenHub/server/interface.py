##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from zope.component.interfaces import Interface
from zope.interface import Attribute


class IHubServerConfig(Interface):
    """An object providing service manager configuration data."""

    metric_priority_map = Attribute(
        "Maps metric names to ServiceCallPriority values.",
    )

    priorities = Attribute(
        "A sequence containing ServiceCallPriority's priority names.",
    )

    executors = Attribute("Maps worklist names to Executor objects.")

    routes = Attribute("Maps ServiceCalls to worklist names.")

    modeling_pause_timeout = Attribute(
        "Number of seconds to wait before resuming the execution "
        "of ServiceCalls with MODELING priority.",
    )

    task_max_retries = Attribute(
        "Limit the number of times a ServiceCall is retried.",
    )

    pbport = Attribute(
        "The port number the Perspective Broker will listen on.",
    )

    xmlrpcport = Attribute(
        "The port number the XMLRPC server will listen on.",
    )


class IServiceCall(Interface):
    """An object that captures the signature of a ZenHub service call."""

    id = Attribute("Uniquely identifies this instance")  # noqa: A003
    monitor = Attribute("Name of the caller's collection monitor")
    service = Attribute("Name of the service")
    method = Attribute("Name of the method on the service")
    args = Attribute("The positional arguments to the method")
    kwargs = Attribute("The keyword arguments to the method")


class IServiceCallRouter(Interface):
    """Maps ServiceCall objects to executor objects."""

    def get(call):
        """Return an IServiceExecutor for the given IServiceCall.

        :type call: IServiceCall
        :rtype: IServiceExecutor
        """


class IServiceExecutor(Interface):
    """An object that executes submitted IServiceCall tasks."""

    def submit(servicecall):
        """Submit an IServiceCall for asynchronous execution.

        The returned Deferred object is fired when the call has completed.

        :type servicecall: IServiceCall
        :rtype: twisted.internet.defer.Deferred
        """
