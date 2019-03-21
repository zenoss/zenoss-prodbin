##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from twisted.internet import defer
from zope.interface import implementer

from .base import IAsyncDispatch


@implementer(IAsyncDispatch)
class EventDispatcher(object):
    """An executor that executes sendEvent and sendEvents methods
    on the EventService service.
    """

    routes = (
        ("EventService", "sendEvent"),
        ("EventService", "sendEvents"),
    )

    def __init__(self, eventmanager):
        """Initializes an EventDispatcher instance.

        @param eventmanager {dmd.ZenEventManager} the event manager
        """
        self.__zem = eventmanager

    def submit(self, job):
        """Submits a job for execution.

        Returns a deferred that will fire when execution completes.
        """
        method = getattr(self.__zem, job.method, None)
        if method is None:
            return defer.fail(AttributeError(
                "No method named '%s' on '%s'" % (job.method, job.service)
            ))
        try:
            state = method(*job.args, **job.kwargs)
        except Exception as ex:
            return defer.fail(ex)
        else:
            return defer.succeed(state)
