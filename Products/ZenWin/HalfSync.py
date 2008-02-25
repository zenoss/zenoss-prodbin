import threading
import time

class Thread(threading.Thread):

    def __init__(self, callback, callable, *args, **kw):
        self.callback = callback
        self.callable = callable
        self.args = args
        self.kw = kw
        threading.Thread.__init__(self)

    def run(self):
        try:
            self.result = (True, self.callable(*self.args, **self.kw))
        except Exception, ex:
            self.result = (False, ex)
            raise
        self.callback(self)

class TooManyThreads(Exception): pass
class TimeoutError(Exception): pass

class HalfSync(object):
    """Go do some synchronous, possibly long-running call.
    Bound that call by a timer.

    If the call succeeds, then return a value, else throw an exception.

    The tricky bit, is that whatever data you have bound into the thread
    will still be running within the thread.  Therefore, you should write your
    callable to do as little internal state mucking around as possible.
    """

    def __init__(self, maxThreads=100):
        self.maxThreads = maxThreads
        self.runningThreads = []
        self.lock = threading.Condition()

    def running(self):
        self.lock.acquire()
        try:
            return len(self.runningThreads) > 0
        finally:
            self.lock.release()


    def boundedCall(self, timeout, callable, *args, **kw):
        """submit work to the thread, poll for results. If the timer is
        hit, throw an exception and tell the thread that it's just
        too late so that it doesn't do anything with the results"""
        self.lock.acquire()
        try:
            if len(self.runningThreads) > self.maxThreads:
                raise TooManyThreads()
            t = Thread(self.callback, callable, *args, **kw)
            self.runningThreads.append(t)
            t.start()
            now = time.time()
            stop = now + timeout
            while 1:
                if t not in self.runningThreads: break
                now = time.time()
                if now > stop: break
                self.lock.wait(stop - now)

            if t in self.runningThreads:
                raise TimeoutError()
            success, value = t.result
            if success:
                return value
            raise value
        finally:
            self.lock.release()
        

    def callback(self, thread):
        self.lock.acquire()
        self.runningThreads.remove(thread)
        self.lock.notify()
        self.lock.release()


            
