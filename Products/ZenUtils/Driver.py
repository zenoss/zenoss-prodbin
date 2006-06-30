#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''Driver.py

Run generators that produce Deferreds.

twisted.flow has something like this, except I cannot understand it.

$Id$
'''

__version__ = "$Revision$"[11:-2]


from twisted.internet import defer, reactor
from twisted.python import failure

class Driver:
    "Walk an iterable that returns a deferred."
    
    def __init__(self):
        self.defer = defer.Deferred()
        self.result = None

    def drive(self, iterable):
        "Call the iterable and set up callbacks to finish"
        self.iter = iterable
        self._next()
        return self.defer

    def _next(self):
        "Move on to the next iterable value"
        try:
            self.iter.next().addBoth(self._finish)
        except StopIteration:
            self.defer.callback(self.result)
        except Exception, ex:
            self.defer.errback(failure.Failure(ex))

    def next(self):
        "Provide the result of the iterable as a value or exception"
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    def _finish(self, result):
        "Store the result of the last deferred for use in next()"
        self.result = result
        self._next()

def drive(callable):
    '''Typical use of Driver class:

    def walk(driver):
        yield thing1()
        print "Thing 1 is", driver.next()
        yeild thing2()
        print "Thing 2 is", driver.next()

    drive(walk)

    '''
    d = Driver()
    return d.drive(callable(d))


def driveLater(secs, callable):
    "Drive the callable at a later time"
    def driveAgain():
        drive(callable)
    reactor.callLater(secs, driveAgain)


def test():
    lst = []
    def loop(d):
        for i in range(10):
            yield defer.succeed(i)
            lst.append(d.next())
    def final(v):
        assert lst[-1] == v
    drive(loop).addCallback(final)
    assert lst == range(10)
    def unloop(d):
        yield defer.fail(ZeroDivisionError('hahaha'))
        d.next()
    def checkError(err):
        assert isinstance(err.value, ZeroDivisionError)
    drive(unloop).addErrback(checkError)
        

if __name__ == '__main__':
    test()
