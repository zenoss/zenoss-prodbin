##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from functools import wraps


def coroutine(func):
    """Decorator for initializing a generator as a coroutine."""

    @wraps(func)
    def start(*args, **kw):
        coro = func(*args, **kw)
        coro.next()
        return coro

    return start


def make_iterable(args):
    if isinstance(args, basestring):
        return (args,)
    elif not hasattr(args, "__iter__"):
        return (args,)
    return args
