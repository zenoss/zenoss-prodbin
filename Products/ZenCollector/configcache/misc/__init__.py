##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import sys as _sys

from functools import wraps as _wraps


def coroutine(func):
    """Decorator for initializing a generator as a coroutine."""

    @_wraps(func)
    def start(*args, **kw):
        coro = func(*args, **kw)
        coro.next()
        return coro

    return start


def into_tuple(args):
    if isinstance(args, basestring):
        return (args,)
    elif not hasattr(args, "__iter__"):
        return (args,)
    return args


def app_name():
    fn = _sys.argv[0].rsplit("/", 1)[-1]
    return fn.rsplit(".", 1)[0] if fn.endswith(".py") else fn
