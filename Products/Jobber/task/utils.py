##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import functools
import inspect
import random
import threading
import transaction

from ZODB.POSException import ConflictError, ReadConflictError
from zope.component import getUtility

from ..interfaces import IJobStore
from ..zenjobs import app


def requires(*features):
    """Return a custom Task deriving from the given features.

    The method resolution order of the created custom task class is
    (*features, ZenTask, celery.app.task.Task, object) where 'features'
    are the classes given to this function.
    """
    bases = tuple(features) + (app.Task, object)
    culled = []
    for feature in reversed(bases):
        for cls in reversed(inspect.getmro(feature)):
            if cls not in culled:
                culled.insert(0, cls)
    name = ''.join(t.__name__ for t in features) + "Task"
    basetask = type(name, tuple(culled), {"abstract": True})
    return basetask


def job_log_has_errors(task_id):
    """Return True if the job's log contains any ERROR messages.
    """
    storage = getUtility(IJobStore, "redis")
    logfile = storage.getfield(task_id, "logfile")
    if not logfile:
        return False
    try:
        with open(logfile, "r") as f:
            return any(
                "ERROR zen." in line
                for line in f.readlines()
            )
    except Exception:
        return False


def transact(f, retries, numbers, sleep=None, ctx=None):
    """Transactional version of f with backoff between retries.

    :param int retries: maximum number of retries before giving up.
    :param numbers: An infinite generator of floats.
    :param sleep: An object that has a wait() method that accepts a float
        produced by numbers.
    :param ctx: the transaction having commit and abort methods.
    """

    sleeper = threading.Event() if sleep is None else sleep
    tx = transaction if ctx is None else ctx

    @functools.wraps(f)
    def transactional(*args, **kw):
        tries_remaining = retries

        while tries_remaining:
            tries_remaining -= 1
            try:
                result = f(*args, **kw)
                tx.commit()
                return result
            except (ReadConflictError, ConflictError):
                # abort immediately to free up resources
                tx.abort()
                if not tries_remaining:
                    raise
                duration = next(numbers)
                sleeper.wait(duration)
                # Reset transaction again to "catch up" to current changes.
                tx.abort()

        raise RuntimeError("Couldn't commit transaction")

    return transactional


def backoff(limit, numbers):
    """Returns a float producing infinite generator.

    The backoff generator will produce a range of floats corresponding to the
    distribution of values produced from the numbers generator.  In general,
    the values are in the range of 0 < x <= limit.

    The numbers function accepts a number and returns a generator that
    produces floats.

    @param int limit: The largest number possible that can be returned.
    @param numbers: A function that takes a float and returns
        an infinite generator.
    @type numbers: Callable[float, Generator]
    """
    maxv = float(limit) / 2
    gen = numbers(maxv)
    while True:
        base = next(gen)
        offset = random.uniform(0, base)
        yield base + offset


def fibonacci(max_value):
    """An infinite generator returning Fibonacci number <= max_value.
    """
    a, b = 0, 1  # the zero is never emitted from the generator.
    while True:
        if b <= max_value:
            a, b = b, a + b
        yield a
