#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

"""When monitoring systems, we often want to repeat some set of
tasks.  This is a fairly simple thing to do, but there are some
complex requirements we desire:

1) When repeating, smooth individual tasks out over the cycle
to spread the load on the machine and its networks between requests.

We don't want 5 seconds of intense activity and then 1 minute of delay.
We want 1 minute of low-level activity.

[Not Implemented]

2) Run tasks in parallel, but limit the number running in parallel.

Some resources, like system network buffers cannot handle a storm
of communications without dropping packets.

4) When repeating, some tasks will fail.  Repeat these failing tasks
less often.

5) If all the tasks do not complete in a cycle, allow one more cycle
for them to complete.  If they still do not complete, note the
failures and restart the whole thing.
"""

from twisted.internet import defer, reactor
import time

import logging
log = logging.getLogger("zen.Repeat")

class RepeatableTask:
    "The interface for tasks given to Repeat"
    
    def start(self):
        "begin executing the task, returns a deferred"

    def name(self):
        "return a string to identify this task in log messages"

WaitStates = 'Waiting InProgress Finished'.split()
for _n, _w in enumerate(WaitStates):
    locals()[_w] = _n

class TaskState:
    "Track the status of a task"    
    def __init__(self, task):
        self.task = task
        self.errorCount = 0
        self.state = Waiting

class BasicRepeat:
    """Repeatedly execute a sequence of Tasks, with no more than N
    tasks active at any one time."""
    
    def __init__(self, chunkSize, cycleTime):
        self.chunkSize 		= chunkSize
        self.cycleTime 		= cycleTime
        self.tasks		= []
        self.startTime		= 0.0
        self.cycle 		= 0


    def start(self, taskSeq):
        "start repeating the tasks"
        self.tasks = map(TaskState, taskSeq)
        self.restart()


    def restart(self):
        "start a new cycle with the tasks"
        self.cycle += 1
        for t in self.tasks:
            t.state = Waiting
        self.startTime = time.time()
        while self.inProgress() < self.chunkSize and self.startTask():
            pass
        reactor.callLater(self.cycleTime, self.cycleTimeout)


    def startTask(self):
        "fire up the next waiting task and return it, if any"
        for t in self.tasks:
            if t.state == Waiting:
                d = t.task.start()
                t.state = InProgress
                args = (t, self.cycle)
                d.addCallbacks(self.finishedTask, self.errorTask,
                               callbackArgs=args, errbackArgs=args)
                return t
        return None
    

    # not fast, but the storage is simpler
    def count(self, state):
        "count the tasks in the given state"
        result = 0
        for t in self.tasks:
            if t.state == state:
                result += 1
        return result


    def finished(self):
        "Return the number of tasks in the Finished state"
        return self.count(Finished)

    
    def waiting(self):
        "Return the number of tasks in the Waiting state"
        return self.count(Waiting)


    def inProgress(self):
        "Return the number of tasks in the InProgress state"
        return self.count(InProgress)

    
    def finishedTask(self, result, task, cycle):
        'successful task completion callback'
        # Did this succeed in the same cycle that it was started?
        if cycle != self.cycle:
            task.errorCount += 1
        else:
            task.state = Finished
            task.errorCount = 0
        if self.finished() == len(self.tasks):
            self.cycleComplete()
        else:
            self.startTask()
        return result


    def errorTask(self, err, task, cycle):
        'failed task completion callback'
        task.state = Finished
        task.errorCount += 1
        if self.finished() == len(self.tasks):
            self.cycleComplete()
        else:
            self.startTask()
        return err


    def cycleTimeout(self, restart=False):
        unfinished = len(self.tasks) - self.finished()
        if unfinished == 0:
            self.restart()
        else:
            if restart:
                log.error("There are %d tasks that are unfinished, "
                          "forcing cycle restart.", unfinished)
                names = []
                for t in self.tasks:
                    if t.state != Finished:
                        names.append(t.task.name())
                        t.state = Finished
                        t.errorCount += 1
                log.debug("Outstanding tasks: %s", " ".join(names))
                self.cycleComplete()
                self.restart()
            else:
                log.warning("There are %d tasks that are unfinished, "
                            "waiting %.1f seconds longer",
                            unfinished,
                            self.cycleTime)
                reactor.callLater(self.cycleTime, self.cycleTimeout, True)

    def cycleComplete(self):
        "hook for noting end-of-cycle"
        pass


class Repeat:
    "Use two basic repeat objects to implement the normal and failing cycles"
    
    def __init__(self, chunkSize, cycleTime, failCycleCount, failCycleTime):
        self.normal = BasicRepeat(chunkSize, cycleTime)
        self.failing = BasicRepeat(chunkSize, failCycleTime)
        self.failCycleCount = failCycleCount

        self.normal.cycleComplete = self.normalCycleComplete
        self.failing.cycleComplete = self.failCycleComplete
        
    def start(self, taskSeq):
        "start repeating the tasks"
        self.normal.start(taskSeq)
        self.failing.start([])
        
    def cycleComplete(self):
        "hook for noting end-of-cycle"
        pass

    def normalCycleComplete(self):
        "hook for noting end-of-cycle for normal tasks"

        # scan for failures
        for t in self.normal.tasks:
            if t.errorCount >= self.failCycleCount:
                self.normal.tasks.remove(t)
                self.failing.tasks.append(t)

        self.cycleComplete()

    def failCycleComplete(self):
        "hook for noting end-of-cycle for failing tasks"
        # scan for successes
        for t in self.failing.tasks:
            if t.errorCount == 0:
                self.failing.tasks.remove(t)
                self.normal.tasks.append(t)

if __name__ == '__main__':
    logging.basicConfig()
    log.setLevel(10)
    
    class TestTask:
        seconds = None

        def __init__(self, seconds):
            self.seconds = seconds
        
        def start(self):
            result = defer.Deferred()
            reactor.callLater(self.seconds, result.callback, self.seconds)
            return result

        def name(self):
            return '%s: %s' % (id(self), `self.seconds`)

    class RepeatStop(Repeat):
        def cycleComplete(self):
            print 'cycleComplete'
            print 'Normal', len(self.normal.tasks), 'Failing', len(self.failing.tasks)
            # reactor.stop()

    repeat = RepeatStop(4, 4, 2, 10)
    repeat.start([TestTask(9), TestTask(9), TestTask(1), TestTask(2),
                  TestTask(1), TestTask(4), TestTask(1), TestTask(2)])
    reactor.run()

__all__ = ['BasicRepeat', 'Repeat', 'RepeatableTask'] + WaitStates
