##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import collections

from twisted.internet import defer
from zope.interface import implementer

from .base import IAsyncDispatch


class NoDispatchRoutes(Warning):
    """A warning indicating a dispatcher has no routes defined.

    This warning is raised if a dispatcher is registered as a non default
    service dispatcher.
    """


@implementer(IAsyncDispatch)
class DispatchingExecutor(object):
    """An dispatcher that maps service/method calls to other dispatchers.

    DispatchingExecutor maintains a registry of dispatchers that maps
    service/method calls to specific dispatcher instances.
    """

    def __init__(self, dispatchers=None, default=None):
        """Initialize a DispatchingExecutor instance.

        @param dispatchers {[IAsyncDispatch,]} Sequence of dispatchers
        @param default {IAsyncDispatch} Default dispatcher if the registry
            doesn't contain an appropriate dispatcher.
        """
        self.__registry = {}
        self.__default = default
        if dispatchers is None:
            dispatchers = []
        elif not isinstance(dispatchers, collections.Sequence):
            dispatchers = [dispatchers]
        for dispatcher in dispatchers:
            self.register(dispatcher)

    @property
    def default(self):
        """Return the default dispatcher.
        """
        return self.__default

    @default.setter
    def default(self, dispatcher):
        """Sets the default dispatcher
        """
        self.__default = dispatcher

    @property
    def dispatchers(self):
        """Returns a sequence containing the registered dispatchers.

        The returned sequence does not include the default dispatcher.
        """
        return tuple(self.__registry.values())

    def register(self, dispatcher):
        """Register a dispatcher for a service and method.

        A ValueError exception is raised if the given dispatcher tries to
        map a service/method route already mapped by another dispatcher.

        @param dispatcher {IAsyncDispatch} dispatcher to register
        """
        entries = {
            (service, method): dispatcher
            for service, method in dispatcher.routes
        }
        if not entries:
            raise NoDispatchRoutes(
                "Dispatcher '%s' has not defined any routes" % (
                    dispatcher.__class__.__name__
                )
            )
        already_defined = set(entries) & set(self.__registry)
        if already_defined:
            raise ValueError(
                "Dispatcher already defined on route(s): %s", ', '.join(
                    "('%s', '%s')" % r for r in already_defined
                )
            )

        self.__registry.update(entries)

    @defer.inlineCallbacks
    def submit(self, job):
        """Submits a job for execution.

        Returns a deferred that will fire when execution completes.
        """
        dispatcher = self.__registry.get(
            (job.service, job.method), self.__default
        )
        if dispatcher is None:
            raise RuntimeError(
                "No dispatcher found that can execute method '%s' on "
                "service '%s'" % (job.method, job.service)
            )
        state = yield dispatcher.submit(job)
        defer.returnValue(state)
