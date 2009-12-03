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

from zope.interface import Interface

class IDeviceLoader(Interface):
    """
    Object with ability to add devices to the database.
    """
    def load_device():
        """
        Attempt to load a single device into the database.
        """

    def load_devices():
        """
        Attempt to load multiple devices into the database.
        """

class IIndexed(Interface):
    """
    Object with ability to keep itself indexed in one or more catalogs.
    """
    def index_object():
        pass
    def unindex_object():
        pass


class IDataRoot(Interface):
    """
    Marker interface for the DMD, so it can be looked up as a global utility.
    """

class IZenDocProvider(Interface):
    """
    Adapter that does zendoc manipulation for an underlying object
    """
    def getZendoc():
        """
        retrieves zendoc text
        """
        pass

    def setZendoc(zendocText):
        """
        set zendoc text
        """
        pass

    def exportZendocXml(self):
        pass
        