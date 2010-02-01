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

from zope.interface import Interface, Attribute


class IFacade(Interface):
    """
    An API facade
    """

class IMarshaller(Interface):
    """
    An adapter that converts an object to a dictionary
    """

    def marshal(keys=None):
        """
        Convert an object to a dictionary.
        """


class IUnmarshaller(Interface):
    """
    An adapter that converts a dictionary to an object.
    """

    def unmarshal(data):
        """
        Convert a dictionary to an object.
        """


class IMarshallable(Interface):
    """
    Marker interface for an object able to be marshalled by an IMarshaller.
    """


class IDataRootFactory(Interface):
    """
    Returns a DataRoot object from the current connection.
    """


class IInfo(Interface):
    """
    A simple representation of an object that can be transformed and serialized
    easily.
    """
    id = Attribute("Identifier of the represented object (usually path)")
    name = Attribute("Name of the represented object")


class IInstanceInfo(IInfo):
    """
    An info adapter that wraps a instance object, where an instance object is
    one that is typically found in an instances relationship of a 'Class'
    object.  Examples of instance objects are OSProcess, IPService and
    WinService.
    """
    device = Attribute("The device associated with this instance")
    monitored = Attribute("Is the instance monitored")
    status = Attribute("What is the status of the instance")


class IInstance(Interface):
    """
    An IInstance object is one that is typically found in an instances
    relationship of a 'Class' object.  Examples of instance objects are
    OSProcess, IPService and WinService.
    """


from events import *
from process import *
from service import *
from device import *
from info import *
from tree import *
from template import *
