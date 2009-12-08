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

from zope.interface import implements
from zope.component import adapts
from Products.Zuul.interfaces import IMarshaller
from Products.Zuul.interfaces import IUnmarshaller
from Products.Zuul.interfaces import IInfo

def _marshalImplicitly(obj):
    """
    Return a dictionary with all the attributes of obj except methods, and
    those that begin with '_'
    """
    variables = vars(obj.__class__).copy()
    variables.update(vars(obj))
    data = {}
    for key in variables:
        if not key.startswith('_'):
            # it is important to use getattr instead of the value in
            # variables, so properties/descriptors work correctly
            value = getattr(obj, key)
            if not callable(value):
                data[key] = value
    return data

def _marshalExplicitly(obj, keys):
    """
    Convert obj to a dict filtering the results based on a list of keys that
    is passed in.
    """
    data = {}
    for key in keys:
        value = getattr(obj, key)
        if callable(value):
            data[key] = value()
        else:
            data[key] = value
    return data

class DefaultMarshaller(object):
    """
    Uses a implicit mashalling if keys is None otherwise uses explicit
    marshalling.
    """
    implements(IMarshaller)
    adapts(IInfo)

    def __init__(self, obj):
        self._obj = obj

    def marshal(self, keys=None):
        if keys is None:
            data = _marshalImplicitly(self._obj)
        else:
            data = _marshalExplicitly(self._obj, keys)
        return data

class DefaultUnmarshaller(object):
    """
    Sets all the values found in the data dictionary onto the obj object using
    the dictionary keys as the attribute names.  Raises an attribute error if
    any of the keys are not found on the object.
    """
    implements(IUnmarshaller)

    def unmarshal(self, data, obj):
        for key, value in data.iteritems():
            setattr(obj, key, value)
