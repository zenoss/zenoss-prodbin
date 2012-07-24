##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from twisted.internet.defer import Deferred, maybeDeferred
from twisted.internet import reactor

class TwistedExecutor(object):
    """
    Executes up to N callables at a time.  N is determined by the maxParrallel
    used to construct an instance, unlimited by default.
    """
    def __init__(self, maxParrallel=None):
        self._max = maxParrallel
        self._running = 0
        self._taskQueue = []

    def setMax(self, max):
        self._max = max
        reactor.callLater(0, self._runTask)
        
    def getMax(self):
        return self._max
    
    @property
    def running(self):
        return self._running
    
    @property
    def queued(self):
        return len(self._taskQueue)

    
    def submit(self, callable, *args, **kw):
        """
        submit a callable to be executed. A deferred will be returned with the
        the result of the callable.
        """
        deferred = Deferred()
        deferred.addBoth(self._taskFinished)
        task = ExecutorTask(deferred, callable, *args, **kw)
        self._taskQueue.append(task)
        reactor.callLater(0, self._runTask)
        return deferred

    def _runTask(self):
        if self._taskQueue and (self._max is None or self._running < self._max):
            self._running += 1
            task = self._taskQueue.pop(0)
            task()
            reactor.callLater(0, self._runTask)
    
    def _taskFinished(self, result):
        self._running -= 1
        reactor.callLater(0, self._runTask)
        return result


class ExecutorTask(object):
    """
    Used by TwistedExecutor to execute queued tasks
    """
    def __init__(self, deferred, callable, *args, **kw):
        self._callable = callable
        self._args = args
        self._kw = kw
        self._deferred = deferred
        
    def __call__(self):
        deferred =  maybeDeferred(self._callable,*self._args, **self._kw)
        deferred.addCallback(self._finished)
        deferred.addErrback(self._error)
        
    def _finished(self, result):
        self._deferred.callback(result)
        
    def _error(self, result):
        self._deferred.errback(result)
