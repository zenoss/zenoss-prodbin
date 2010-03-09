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

"""
The concept of an interface is part of the Zope Component Architecture (ZCA).
Interfaces are used in the Zuul Python API to document the attributes of the 
interface implementations.  Using interfaces also allows the facades to get
info objects that adapt a ZenModel object, e.g. IInfo(self._dmd.Devices).  The
definition that determines the concrete implementation returned by such a
statement is in Zuul/configure.zcml.
"""

from zope.interface import Interface, Attribute


class IFacade(Interface):
    """
    An API facade
    """
    context = Attribute('The context of the adapter.')


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


from events import *
from process import *
from service import *
from device import *
from component import *
from info import *
from tree import *
from template import *
from command import *
from network import *
