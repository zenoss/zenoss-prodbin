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

import AccessControl
from zope import component
from zope.interface import verify
from interfaces import IFacade, IInfo
from interfaces import IMarshallable
from interfaces import IMarshaller
from interfaces import IUnmarshaller
from interfaces import IDataRootFactory
from utils import safe_hasattr as hasattr

def getFacade(name):
    """
    Get facade by name. 
    """
    return component.getUtility(IFacade, name)


def marshal(obj, keys=None, marshallerName=''):
    """
    Convert an object to a dictionary. keys is an optional list of keys to
    include in the returned dictionary.  if keys is None then all public
    attributes are returned.  marshallerName is an optional marshalling
    adapter name. if it is an empty string then the default marshaller will be
    used.
    """
    # obj is itself marshallable, so make a marshaller and marshal away
    if IMarshallable.providedBy(obj):
        marshaller = component.getAdapter(obj, IMarshaller, marshallerName)
        verify.verifyObject(IMarshaller, marshaller)
        return marshal(marshaller.marshal(keys), keys, marshallerName)

    # obj is a dict, so marshal its values recursively
    # Zuul.marshal({'foo':1, 'bar':2})
    if isinstance(obj, dict):
        return dict((k, marshal(obj[k], keys, marshallerName)) for k in obj)

    # obj is a non-string iterable, so marshal its members recursively
    # Zuul.marshal(set([o1, o2]))
    elif hasattr(obj, '__iter__'):
        return [marshal(o, keys, marshallerName) for o in obj]

    # Nothing matched, so it's a string or number or other unmarshallable. 
    else:
        return obj


def unmarshal(data, obj, unmarshallerName=''):
    """
    Set the values found the the data dictionary on the properties of the same
    name in obj.
    """
    unmarshaller = component.getAdapter(obj, IUnmarshaller, unmarshallerName)
    verify.verifyObject(IUnmarshaller, unmarshaller)
    # Get rid of immutable uid attribute
    if 'uid' in data:
        del data['uid']
    return unmarshaller.unmarshal(data)


def info(obj, adapterName=''):
    """
    Recursively adapt obj or members of obj to IInfo.
    """
    if IInfo.providedBy(obj):
        return obj

    # obj is a dict, so apply to its values recursively
    elif isinstance(obj, dict):
        return dict((k, info(obj[k], adapterName)) for k in obj)

    # obj is a non-string iterable, so apply to its members recursively
    elif hasattr(obj, '__iter__'):
        return [info(o, adapterName) for o in obj]

    # attempt to adapt; if no adapter, return obj itself
    else:
        return component.queryAdapter(obj, IInfo, adapterName, obj)


def checkPermission(permission):
    """
    Return true if the current user has the specified permission on dmd,
    otherwise return false.
    """
    manager = AccessControl.getSecurityManager()
    dmdFactory = component.getUtility(IDataRootFactory)
    dmd = dmdFactory()
    return manager.checkPermission(permission, dmd)
