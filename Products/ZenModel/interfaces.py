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

class IAction(Interface):
    
    def execute(notification, signal):
        """
        @param notification: The notification that should be sent.
        @type notification: NotificationSubscription
        @param signal: The signal that caused this notification to be executed.
        @type signal: zenoss.protocols.protobufs.zep_pb2.Signal
        """
        pass
    

class IProvidesEmailAddresses(Interface):
    def getEmailAddresses():
        pass

class IProvidesPagerAddresses(Interface):
    def getPagerAddresses():
        pass

class IProcessSignal(Interface):

    def process(signal):
        """
        @param signal: The signal that may require additional processing
        @type signal: zenoss.protocols.protobufs.zep_pb2.Signal
        """
        pass
