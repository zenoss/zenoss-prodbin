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

import os

import logging
log = logging.getLogger('zen.thresholds')

class Thresholds:
    "Class for holding multiple Thresholds, used in most collectors"

    def __init__(self):
        self.thresholds = {}
        self.map = {}

    def remove(self, threshold):
        doomed = self.thresholds.get(threshold.key(), None)
        if doomed:
            del self.thresholds[doomed.key()]
            ctx = doomed.context()
            for dp in doomed.dataPoints():
                lst = self.map[ctx.fileKey(dp)]
                if (doomed, dp) in lst:
                    lst.remove( (doomed, dp) )
                if not lst:
                    del self.map[ctx.fileKey(dp)]
        return doomed

    def add(self, threshold):
        self.thresholds[threshold.key()] = threshold
        ctx = threshold.context()
        for dp in threshold.dataPoints():
            self.map.setdefault(ctx.fileKey(dp), []).append((threshold, dp))
        
    def update(self, threshold):
        "Store a threshold instance for future computation"
        log.debug("Updating threshold %r", threshold.key())
        doomed = self.remove(threshold)
        if doomed:
            threshold.count = doomed.count
        self.add(threshold)

    def updateList(self, thresholds):
        "Store a threshold instance for future computation"
        for threshold in thresholds:
            self.update(threshold)

    def check(self, filename, timeAt, value):
        "Check a given threshold based on an updated value"
        result = []
        if filename in self.map:
            log.debug("Checking value %s on %s", value, filename)
            for t, dp in self.map[filename]:
                result += t.checkRaw(dp, timeAt, value)
        return result

def test():
    pass

if __name__ == '__main__':
    test()

