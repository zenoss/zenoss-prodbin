###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import warnings
import functools
from AccessControl import Unauthorized
from Products import Zuul


def deprecated(func):
    """
    This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.
    """

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        warnings.warn_explicit(
            "Call to deprecated function %(funcname)s." % {
                'funcname': func.__name__,
            },
            category=DeprecationWarning,
            filename=func.func_code.co_filename,
            lineno=func.func_code.co_firstlineno + 1
        )
        return func(*args, **kwargs)
    return new_func


def decorator(decorator_func):
    """
    Turns a function into a well-behaved decorator.

    Requires the signature (func, *args, **kwargs).

    Updates the inner function to look like the decorated version by
    copying attributes from the one to the other.
    """
    def _decorator(func):
        def inner(*args, **kwargs):
            return decorator_func(func, *args, **kwargs)
        inner.__name__ = func.__name__
        inner.__doc__ = func.__doc__
        inner.__module__ = func.__module__
        try:
            inner.__dict__.update(func.__dict__)
        except:
            pass
        return inner
    return _decorator


@decorator
def marshal(f, *args, **kwargs):
    result = f(*args, **kwargs)
    return Zuul.marshal(result)


def marshalto(keys=None, marshallerName=''):
    @decorator
    def marshal(f, *args, **kwargs):
        result = f(*args, **kwargs)
        return Zuul.marshal(result, keys=keys, marshallerName=marshallerName)
    return marshal


@decorator
def info(f, *args, **kwargs):
    """
    Apply Zuul.info to results.
    """
    result = f(*args, **kwargs)
    return Zuul.info(result)


def infoto(adapterName=''):
    @decorator
    def info(f, *args, **kwargs):
        result = f(*args, **kwargs)
        return Zuul.info(result, adapterName=adapterName)
    return info


@decorator
def memoize(f, *args, **kwargs):
    sig = repr((args, kwargs))
    cache = f._m_cache = getattr(f, '_m_cache', {})
    if sig not in cache:
        cache[sig] = f(*args, **kwargs)
    return cache[sig]


def require(permission):
    """
    Decorator that checks if the current user has the permission. Only valid on
    IFacade objects.
    """
    @decorator
    def wrapped_fn(f, self, *args, **kwargs):
        if not Zuul.checkPermission(permission, self.context):
            args = (f.__name__, permission)
            raise Unauthorized('Calling %s requires "%s" permission.' % args)
        return f(self, *args, **kwargs)
    return wrapped_fn


def contextRequire(permission, contextKeywordArgument):
    """
    Decorator that checks if the current user has the permission on a passed in context.
    The argument can be either the unique string of an object (uid) or the object itself.

    NOTE: This decorator assumes that the arguments to the method will be passed
    in as keyword arguments.  It is mainly used by the routers where this is the
    case.
    """
    @decorator
    def wrapped_fn(f, self, *args, **kwargs):
        context = kwargs[contextKeywordArgument]
        if isinstance(context, basestring):
            context = self.context.unrestrictedTraverse(context)
        if not Zuul.checkPermission(permission, context):
            args = (f.__name__, permission)
            raise Unauthorized('Calling %s requires "%s" permission.' % args)
        return f(self, *args, **kwargs)
    return wrapped_fn
