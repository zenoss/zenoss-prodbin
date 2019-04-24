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
from zope.component import getUtility

from Products.Zuul.interfaces import IDataRootFactory


class SendEventExecutor(object):
    """Executes sendEvent and sendEvents tasks.

    This executor bypasses the EventService and executes the sendEvent
    and sendEvents tasks directly on a MySqlEventManager instance.
    """

    def __init__(self, name):
        """Initialize an SendEventExecutor instance.

        :param str name: the name of this executor
        """
        self.__name = name
        self.__zem = getUtility(IDataRootFactory)().ZenEventManager

    @property
    def name(self):
        return self.__name

    def start(self, reactor):
        pass

    def submit(self, call):
        """Submit a ServiceCall for execution.

        Returns a deferred that will fire when execution completes.
        """
        if call.method not in ("sendEvent", "sendEvents"):
            return defer.fail(TypeError(
                "%s does support executing method '%s'"
                % (type(self).__name__, call.method),
            ))
        method = getattr(self.__zem, call.method, None)
        if method is None:
            return defer.fail(AttributeError(
                "%s has no method '%s'"
                % (self.__zem.__class__.__name__, call.method),
            ))

        try:
            state = method(*call.args, **call.kwargs)
        except Exception as ex:
            return defer.fail(ex)
        else:
            return defer.succeed(state)
