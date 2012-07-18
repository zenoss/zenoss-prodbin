###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import logging
from twisted.internet import reactor, defer


log = logging.getLogger('zen.Procrastinator')


class Procrastinate(object):
    "A class to delay executing a change to a device"

    _DO_LATER_DELAY = 5
    _DO_NOW_DELAY = 0.05

    def __init__(self, cback):
        self.cback = cback
        self.devices = set()
        self.timer = None
        self._stopping = False
        self._stopping_deferred = defer.Deferred()

    def clear(self):
        self.devices = set()

    def stop(self):
        self._stopping = True
        if not self.devices:
            return defer.succeed(True)
        log.debug("Returning stopping deferred")
        d, self._stopping_deferred = self._stopping_deferred, None
        return d

    def doLater(self, device = None):
        if not self._stopping:
            if self.timer and not self.timer.called:
                self.timer.cancel()
            self.devices.add(device)
            self.timer = reactor.callLater(Procrastinate._DO_LATER_DELAY, self._doNow)

    def _doNow(self, *unused):
        if self.devices:
            device = self.devices.pop()
            self.cback(device)
            if self.devices:
                reactor.callLater(Procrastinate._DO_NOW_DELAY, self._doNow)
            elif self._stopping:
                log.debug("Callback to _stopping_deferred")
                self._stopping_deferred.callback(None)
