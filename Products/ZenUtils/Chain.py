#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''Chain

Chain a series of deferred actions serially.

$Id$
'''

__version__ = "$Revision$"[11:-2]



from twisted.internet import defer

class Chain:
    """Takes an interable of callables, which return deferred, and
    returns the results of calling all those functions and waiting
    on the defers"""

    def __init__(self, sequence):
        self.callables = sequence
        self.results = []
        self.defer = defer.Deferred()

    def run(self):
        self.next()
        return self.defer

    def next(self):
        "run the next step"
        try:
            next = self.callables.next()
            next().addCallbacks(self.success, self.failure)
        except StopIteration:
            self.defer.callback(self.results)

    def success(self, result):
        "gather a successful result"
        self.results.append((True, result))
        self.next()

    def failure(self, result):
        "gather an error result"
        self.results.append((False, result))
        self.next()

