##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import socket
import time

from twisted.spread import pb

from Products.ZenUtils.deprecated import deprecated


class HubService(object, pb.Referenceable):
    """
    The base class for a ZenHub service class.

    :attr log: The logger object for this service.
    :type log: logging.Logger
    :attr fqdn: This attribute is deprecated.
    :type fqdn: str
    :attr dmd: Root ZODB object
    :type dmd: Products.ZenModel.DataRoot.DataRoot
    :attr instance: The name of the Collection Hub.
    :type instance: str
    :attr callTime: The total time, in seconds, this service has spent processing remote requests.
    :type callTime: float

    :attr listeners: ZenHub clients for this service
    :type listeners: List[twisted.spread.pb.RemoteReference]
    :attr listenerOptions: Options associated with the client for this service.
    :type listenerOptions: Mapping[twisted.spread.pb.RemoteReference, Mapping[Any, Any]]
    """  # noqa E501

    def __init__(self, dmd, instance):
        self.log = logging.getLogger("zen.hub")
        self.fqdn = socket.getfqdn()
        self.dmd = dmd
        self.zem = dmd.ZenEventManager
        self.instance = instance
        self.listeners = []
        self.listenerOptions = {}
        self.callTime = 0

    def getPerformanceMonitor(self):
        return self.dmd.Monitors.getPerformanceMonitor(self.instance)

    def remoteMessageReceived(self, broker, message, args, kw):
        self.log.debug("Servicing %s in %s", message, self.name())
        now = time.time()
        try:
            return pb.Referenceable.remoteMessageReceived(
                self, broker, message, args, kw
            )
        finally:
            secs = time.time() - now
            self.log.debug("Time in %s: %.2f", message, secs)
            self.callTime += secs

    @deprecated
    def update(self, object):
        # FIXME: No longer called
        pass

    @deprecated
    def deleted(self, object):
        # FIXME: No longer called
        pass

    def name(self):
        return self.__class__.__name__

    def addListener(self, remote, options=None):
        remote.notifyOnDisconnect(self.removeListener)
        self.log.debug("adding listener for %s:%s", self.instance, self.name())
        self.listeners.append(remote)
        if options:
            self.listenerOptions[remote] = options

    def removeListener(self, listener):
        self.log.debug(
            "removing listener for %s:%s", self.instance, self.name()
        )
        try:
            self.listeners.remove(listener)
        except ValueError:
            self.warning("Unable to remove listener... ignoring")

        self.listenerOptions.pop(listener, None)

    def sendEvents(self, events):
        map(self.sendEvent, events)

    def sendEvent(self, event, **kw):
        event = event.copy()
        event["agent"] = "zenhub"
        event["monitor"] = self.instance
        event["manager"] = self.fqdn
        event.update(kw)
        self.zem.sendEvent(event)
