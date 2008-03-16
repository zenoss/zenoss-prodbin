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
hubLog = logging.getLogger("zenhub")
import time

def threaded(callable):
    from twisted.internet import reactor
    from twisted.internet.defer import Deferred

    def callInThread(*args, **kw):
        "Run the callable in a separate thread."

        def run(deferred, callable, *args, **kw):
            try:
                reactor.callFromThread(deferred.callback, callable(*args, **kw))
            except Exception, ex:
                reactor.callFromThread(deferred.errback, (ex))
        d = Deferred()
        reactor.callInThread(run, d, callable, *args, **kw)
        return d
    return callInThread

class HubService(pb.Referenceable):

    log = hubLog

    def __init__(self, dmd, instance):
        self.dmd = dmd
        self.zem = dmd.ZenEventManager
        self.instance = instance
        self.listeners = []
        self.callTime = 0.

    def remoteMessageRecieved(self, broker, message, args, kw):
        now = time.time()
        try:
            return pb.Referenceable.remoteMessageRecieved(self, broker, message, args, kw)
        finally:
            self.callTime += time.time() - now

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
