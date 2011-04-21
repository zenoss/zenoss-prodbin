###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from zope.interface import Interface, Attribute
from zope.component.interfaces import IObjectEvent


class IGloballyIdentifiable(Interface):
    """
    An object with a GUID.
    """
    def getPrimaryUrlPath():
        """
        The path under which the object can be found.
        """


class IGlobalIdentifier(Interface):
    """
    Adapter that manages GUID for objects.
    """
    def __init__(context):
        """
        Constructor
        """

    guid = Attribute("Globally unique identifier")

    def getGUID():
        """
        Gets the GUID associated with this object.
        """
    def setGUID(value):
        """
        Sets the GUID for this object.
        """
    def create(force):
        """
        Creates a new GUID and applies it to this object.
        """

class IGUIDManager(Interface):
    """
    A utility that can register objects as having guids and look up objects by
    guid.
    """
    def getPath(guid):
        """
        Return the path associated with a guid.
        """
    def getObject(guid):
        """
        Return the object associated with a guid.
        """
    def register(object):
        """
        Store the guid-path mapping in the reference table.
        """

class IGUIDEvent(IObjectEvent):
    pass
