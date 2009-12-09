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

from zope import component
from zope.interface import verify
from interfaces import IFacade
from interfaces import IMarshallable
from interfaces import IMarshaller
from interfaces import IUnmarshaller

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
    _marker = object()

    # obj is a dict, so marshal its values recursively
    # Zuul.marshal({'foo':1, 'bar':2})
    if isinstance(obj, dict):
        return dict((k, marshal(obj[k], keys, marshallerName)) for k in obj)

    # obj is a non-string iterable, so marshal its members recursively
    # Zuul.marshal(set([o1, o2]))
    elif getattr(obj, '__iter__', _marker) is not _marker:
        return [marshal(o, keys, marshallerName) for o in obj]

    # obj is itself marshallable, so make a marshaller and marshal away
    elif IMarshallable.providedBy(obj):
        marshaller = component.getAdapter(obj, IMarshaller, marshallerName)
        verify.verifyObject(IMarshaller, marshaller)
        return marshaller.marshal(keys)

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
    return unmarshaller.unmarshal(data)
