import sys
import time
import multiprocessing
from functools import wraps


class TimeoutError(Exception):
    def __init__(self, message):
        super(TimeoutError, self).__init__(message)


def timeout(seconds=5):
    def decorate(function):
        @wraps(function)
        def new_function(*args, **kwargs):
            timeout_wrapper = _Timeout(function, seconds)
            return timeout_wrapper(*args, **kwargs)
        return new_function
    return decorate


def _target(queue, function, *args, **kwargs):
    try:
        queue.put((True, function(*args, **kwargs)))
    except:
        queue.put((False, sys.exc_info()[1]))


class _Timeout(object):
    def __init__(self, function, limit):
        self._limit = limit
        self._function = function
        self._timeout = time.time()
        self._process = multiprocessing.Process()
        self._queue = multiprocessing.Queue()

    def __call__(self, *args, **kwargs):
        self._limit = kwargs.pop('timeout', self._limit)
        self._queue = multiprocessing.Queue(1)
        args = (self._queue, self._function) + args
        self._process = multiprocessing.Process(
            target=_target, args=args, kwargs=kwargs)
        self._process.daemon = True
        self._process.start()
        self._timeout = self._limit + time.time()
        while not self.ready:
            time.sleep(0.01)
        return self.value

    def cancel(self):
        if self._process.is_alive():
            self._process.terminate()

        raise TimeoutError("Query timed out after {} seconds".format(self._limit))

    @property
    def ready(self):
        if self._timeout < time.time():
            self.cancel()
        return self._queue.full() and not self._queue.empty()

    @property
    def value(self):
        if self.ready is True:
            flag, load = self._queue.get()
            if flag:
                return load
            raise load

