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
#! /usr/bin/env python 

__doc__='''NJobs

Run a list of jobs in parallel, limited to N at a time.

$Id$
'''

__version__ = "$Revision$"[11:-2]

from twisted.internet import defer


class NJobs:
    "Run a list of jobs in parallel, limited to N at a time."
    
    def __init__(self, max, callable, data):
        self.defer = defer.Deferred()
        self.results = []
        self.max = max
        self.callable = callable
        self.workQueue = data
        self.running = 0

    def start(self):
        self._runSome()
        return self.defer

    def status(self):
        return self.running, len(self.workQueue), len(self.results)

    def _runSome(self):
        while self.running < self.max and self.workQueue:
            self.running += 1
            try:
                d = self.callable(self.workQueue.pop())
            except Exception, ex:
                self._finished(ex)
            else:
                d.addBoth(self._finished)
        if self.running == 0 and not self.workQueue and not self.defer.called:
            self.defer.callback(self.results)

    def _finished(self, result):
        self.running -= 1
        self.results.append(result)
        self._runSome()


