###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from twisted.spread import pb

import logging
import time

def threaded(callable):
    from twisted.internet.threads import deferToThread

    def callInThread(*args, **kw):
        "Run the callable in a separate thread."
        return deferToThread(callable, *args, **kw)
    return callInThread

class HubService(pb.Referenceable):

    def __init__(self, dmd, instance):
        self.log = logging.getLogger('zen.hub')
        self.dmd = dmd
        self.zem = dmd.ZenEventManager
        self.instance = instance
        self.listeners = []
        self.callTime = 0.

    def getPerformanceMonitor(self):
        return self.dmd.Monitors.getPerformanceMonitor(self.instance)

    def remoteMessageReceived(self, broker, message, args, kw):
        now = time.time()
        try:
            return pb.Referenceable.remoteMessageReceived(self, broker, message, args, kw)
        finally:
            secs = time.time() - now
            self.log.debug("Time in %s: %.2f", message, secs)
            self.callTime += secs

    def update(self, object):
        pass

    def deleted(self, object):
        pass

    def addListener(self, remote):
        remote.notifyOnDisconnect(self.removeListener)
        self.log.info("adding listener")
        self.listeners.append(remote)

    def removeListener(self, listener):
        self.log.warning("removing listener")
        try:
            self.listeners.remove(listener)
        except ValueError:
            self.warning("Unable to remove listener... ignoring")
