##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in 
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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


from process import *  # noqa
from service import *  # noqa
from device import *  # noqa
from properties import *  # noqa
from devicemanagement import *  # noqa
from component import *  # noqa
from info import *  # noqa
from tree import *  # noqa
from triggers import *  # noqa
from template import *  # noqa
from command import *  # noqa
from network import *  # noqa
from graphpoint import *  # noqa
from organizer import *  # noqa
from mib import *  # noqa
from zep import *  # noqa
from reportable import *  # noqa
from report import *  # noqa
from stats import *  # noqa
from jobs import *  # noqa
from software import *  # noqa
from devicedumpload import *  # noqa
from eventclasses import *  # noqa
from manufacturers import *  # noqa
from backup import *  # noqa
from metric import *  # noqa
from security import *  # noqa
from application import *  # noqa
from monitor import *  # noqa
from user import *  # noqa
from host import *  # noqa
