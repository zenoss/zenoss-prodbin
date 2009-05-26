###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import simplejson

def json(value):
    """
    Serialize C{value} into a JSON string.

    If C{value} is callable, a decorated version of C{value} that serializes its
    return value will be returned.

        >>> value = (dict(a=1L), u"123", 123)
        >>> print json(value)
        [{"a": 1}, "123", 123]
        >>> @json
        ... def f():
        ...     return value
        ...
        >>> print f()
        [{"a": 1}, "123", 123]

    @param value: An object to be serialized
    @type value: dict, list, tuple, str, etc. or callable
    @return: The JSON representation of C{value} or a decorated function
    @rtype: str, func
    """
    if callable(value):
        # Decorate the given callable
        def inner(*args, **kwargs):
            return simplejson.dumps(value(*args, **kwargs))
        # Well-behaved decorators look like the decorated function
        inner.__name__ = value.__name__
        inner.__dict__.update(value.__dict__)
        inner.__doc__ = value.__doc__
        return inner
    else:
        # Simply serialize the value passed
        return simplejson.dumps(value)

def unjson(value):
    """
    Create the Python object represented by the JSON string C{value}.

        >>> jsonstr = '[{"a": 1}, "123", 123]'
        >>> print unjson(jsonstr)
        [{'a': 1}, '123', 123]
    
    @param value: A JSON string
    @type value: str
    @return: The object represented by C{value}
    """
    return simplejson.loads(value)
