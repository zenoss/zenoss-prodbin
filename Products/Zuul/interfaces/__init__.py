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
    A utility that converts a dictionary to an object.
    """

    def unmarshal(data, obj):
        """
        Convert a dictionary to an object.
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


class ISerializableFactory(Interface):
    """
    Calling implementations of this interface returns a python data structure
    suitable for serialization. The objects that these factories create can be
    passed to json.dumps().
    """
    def __call__():
        """
        Return the serialized object.
        """

from events import *
from process import *
from device import *
from info import *
from tree import *
