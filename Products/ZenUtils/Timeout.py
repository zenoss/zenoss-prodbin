###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from twisted.internet import reactor
from twisted.internet import defer

class TimeoutDeferred(defer.Deferred):
    """A deferred that fires errback if the result doesn't come
    back in the given time period"""

    timer = None
    
    def __init__(self, other, timeout):
        """Wrap the passed deferred and return a new deferred that
        will timeout

        @type other: a Deferred
        @param other: the deferred to wrap
        @type timeout: floating point number
        @param timeout: time, in seconds, to wait before failing the deferred
        """
        defer.Deferred.__init__(self)
        self.timer = reactor.callLater(timeout, self._timeout)
        other.chainDeferred(self)

    def _timeout(self):
        "The wrapped deferred was too slow: fire the errback"
        if not self.called:
            self.timer = None
            self.errback(defer.TimeoutError())

    def _startRunCallbacks(self, result):
        "We have a result, fire callbacks or cancel the timer"
        if self.timer:
            self.timer.cancel()
            self.timer = None
        if not self.called:
            defer.Deferred._startRunCallbacks(self, result)

def timeout(deferred, timeInSeconds):
    "Utility method to wrap a deferred to timeout in timeInSeconds"
    return TimeoutDeferred(deferred, timeInSeconds)
