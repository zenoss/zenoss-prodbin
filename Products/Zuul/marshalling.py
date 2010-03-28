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
from Products.ZenUtils.jsonutils import json
from Products import Zuul
from Products.Zuul.interfaces import IMarshallable
from Products.Zuul.interfaces import IMarshaller
from Products.Zuul.interfaces import IUnmarshaller
from Products.Zuul.interfaces import IInfo
from Products.Zuul.interfaces import IProcessInfo
from Products.Zuul.interfaces import ITreeNode

def _marshalImplicitly(obj):
    """
    Return a dictionary with all the attributes of obj except methods, and
    those that begin with '_'
    """
    data = {}
    for key in dir(obj):
        if not key.startswith('_'):
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
        try:
            value = getattr(obj, key)
        except AttributeError:
            pass
        else:
            if callable(value):
                value = value()
            data[key] = value
    return data


class Marshaller(object):
    """
    Uses a implicit mashalling if keys is None otherwise uses explicit
    marshalling.
    """
    implements(IMarshaller)
    adapts(IMarshallable)

    def __init__(self, obj):
        self._obj = obj

    def marshal(self, keys=None):
        if keys is None:
            data = _marshalImplicitly(self._obj)
        else:
            _keys = set(keys[:]) | set(self.getRequiredKeys())
            data = _marshalExplicitly(self._obj, _keys)
        return data

    def getRequiredKeys(self):
        return []


class InfoMarshaller(Marshaller):
    """
    Uses a implicit mashalling if keys is None otherwise uses explicit
    marshalling.
    """
    adapts(IInfo)

    def getRequiredKeys(self):
        # Ensure that uid makes it through
        return ['uid']


class TreeNodeMarshaller(object):
    """
    Converts a root tree node to a dictionary, recursively marshalling its
    children.
    """
    implements(IMarshaller)
    adapts(ITreeNode)

    def __init__(self, root):
        self.root = root

    def marshal(self, keys=None):
        obj = {}
        for attr in dir(self.root):
            if attr.startswith('_'):
                continue
            val = getattr(self.root, attr)
            try:
                json(val)
            except TypeError:
                # We can't deal with it, just move on
                continue
            obj[attr] = val
        if self.root.leaf:
            obj['leaf'] = True
        else:
            obj['children'] = []
            for childNode in self.root.children:
                obj['children'].append(Zuul.marshal(childNode))
        return obj


class DefaultUnmarshaller(object):
    """
    Sets all the values found in the data dictionary onto the obj object using
    the dictionary keys as the attribute names.  Raises an attribute error if
    any of the keys are not found on the object.
    """
    implements(IUnmarshaller)
    adapts(IInfo)

    def __init__(self, obj):
        self.obj = obj

    def unmarshal(self, data):
        for key, value in data.iteritems():
            setattr(self.obj, key, value)


class ProcessUnmarshaller(object):
    """
    Unmarshalls dictionary into a ProcessInfo object.  Coverts monitor and
    ignoreParameters into boolean values.
    """
    implements(IUnmarshaller)
    adapts(IProcessInfo)

    def __init__(self, obj):
        self.obj = obj

    def unmarshal(self, data):
        for key, value in data.iteritems():
            if key in ['monitor', 'alertOnRestart', 'ignoreParameters']:
                value = True
            setattr(self.obj, key, value)
        if 'isMonitoringAcquired' not in data:
            if 'monitor' not in data:
                setattr(self.obj, 'monitor', False)
            if 'alertOnRestart' not in data:
                setattr(self.obj, 'alertOnRestart', False)
        if 'ignoreParameters' not in data:
            setattr(self.obj, 'ignoreParameters', False)
