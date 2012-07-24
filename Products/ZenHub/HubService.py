##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from twisted.spread import pb

import logging
import time
import socket

class HubService(pb.Referenceable):

    def __init__(self, dmd, instance):
        self.log = logging.getLogger('zen.hub')
        self.fqdn = socket.getfqdn()
        self.dmd = dmd
        self.zem = dmd.ZenEventManager
        self.instance = instance
        self.listeners = []
        self.callTime = 0.
        self.methodPriorityMap = {}

    def getPerformanceMonitor(self):
        return self.dmd.Monitors.getPerformanceMonitor(self.instance)

    def remoteMessageReceived(self, broker, message, args, kw):
        self.log.debug("Servicing %s in %s", message, self.name())
        now = time.time()
        try:
            return pb.Referenceable.remoteMessageReceived(self, broker, message, args, kw)
        finally:
            secs = time.time() - now
            self.log.debug("Time in %s: %.2f", message, secs)
            self.callTime += secs

    def update(self, object):
        # FIXME: No longer called
        pass

    def deleted(self, object):
        # FIXME: No longer called
        pass

    def name(self):
        return self.__class__.__name__

    def addListener(self, remote):
        remote.notifyOnDisconnect(self.removeListener)
        self.log.debug("adding listener for %s:%s", self.instance, self.name())
        self.listeners.append(remote)

    def removeListener(self, listener):
        self.log.debug("removing listener for %s:%s", self.instance, self.name())
        try:
            self.listeners.remove(listener)
        except ValueError:
            self.warning("Unable to remove listener... ignoring")

    def getMethodPriority(self, methodName):
        if methodName in self.methodPriorityMap:
            return self.methodPriorityMap[methodName]
        return 0.2

    def sendEvents(self, events):
        map(self.sendEvent, events)

    def sendEvent(self, event, **kw):
        event = event.copy()
        event['agent'] = 'zenhub'
        event['monitor'] = self.instance
        event['manager'] = self.fqdn
        event.update(kw)
        self.zem.sendEvent(event)
