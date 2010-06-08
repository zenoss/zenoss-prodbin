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

import json as _json
import re

def _recursiveCaster(ob):
    if isinstance(ob, dict):
        result = {}
        for k, v in ob.iteritems():
            result[str(k)] = _recursiveCaster(v)
        return result
    elif isinstance(ob, list):
        return [_recursiveCaster(x) for x in ob]
    elif isinstance(ob, unicode):
        return str(ob)
    else:
        return ob


class StringifyingDecoder(_json.JSONDecoder):
    """
    Casts all unicode objects as strings. This is necessary until Zope is less
    stupid.
    """
    def decode(self, s):
        result = super(StringifyingDecoder, self).decode(s)
        return _recursiveCaster(result)

class JavaScript(object):
    """A simple class that represents a JavaScript literal that should not be JSON encoded."""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

class JavaScriptRegex(JavaScript):
    """A simple class that represents a JavaScript Regex literal that should not be JSON encoded."""
    def __str__(self):
        return '/' + self.value + '/'

class JavaScriptEncoder(_json.JSONEncoder):
    """A JavaScript encoder based on JSON. It encodes like normal JSON except it passes JavaScript objects un-encoded."""

    _js_start = '__js_start__'
    _js_end = '__js_end__'
    _js_re = re.compile(r'\["%s", (.*?), "%s"\]' % (_js_start, _js_end))

    def default(self, obj):
        if isinstance(obj, JavaScript):
            return [self._js_start, str(obj), self._js_end]
        else:
            return _json.JSONEncoder.default(self, obj)

    def _js_clean(self, jsonstr):
        # This re replace is not ideal but at least the dirtyness of it is encapsulated in these classes
        # instead of plain str manipulation being done in the wild.
        def fix(matchobj):
            return _json.loads(matchobj.group(1))

        return self._js_re.sub(fix, jsonstr)

    def encode(self, obj):
        return self._js_clean(_json.JSONEncoder.encode(self, obj))

def json(value, **kw):
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
            return _json.dumps(value(*args, **kwargs))
        # Well-behaved decorators look like the decorated function
        inner.__name__ = value.__name__
        inner.__dict__.update(value.__dict__)
        inner.__doc__ = value.__doc__
        return inner
    else:
        # Simply serialize the value passed
        return _json.dumps(value, **kw)

def javascript(data):
    """A JavaScript encoder based on JSON. It encodes like normal JSON except it passes JavaScript objects un-encoded."""
    return json(data, cls=JavaScriptEncoder)

def unjson(value, **kw):
    """
    Create the Python object represented by the JSON string C{value}.

        >>> jsonstr = '[{"a": 1}, "123", 123]'
        >>> print unjson(jsonstr)
        [{'a': 1}, '123', 123]

    @param value: A JSON string
    @type value: str
    @return: The object represented by C{value}
    """
    if 'cls' not in kw:
        kw['cls'] = StringifyingDecoder
    return _json.loads(value, **kw)
