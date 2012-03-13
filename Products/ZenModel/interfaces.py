###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.interface import Interface, Attribute

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

    id = Attribute("The unique identifier for this action.")
    name = Attribute("The human-friendly name of this action.")
    actionContentInfo = Attribute("The class that adapts a notification to an "
                                  "IInfo object for this class.")

    def getDefaultData(dmd):
        """Return a dictionary of the default data for the notification content"""

    def configure(options):
        """
        @param options: Options to configure the specified action.
        @type  options: Dictionary.
        """
        pass
    
    def execute(notification, signal):
        """
        @param notification: The notification that should be sent.
        @type notification: NotificationSubscription
        @param signal: The signal that caused this notification to be executed.
        @type signal: zenoss.protocols.protobufs.zep_pb2.Signal
        """
        pass

    def getInfo(notification):
        """
        Given a notification, adapt it to it's appropriate ActionContentInfo object.
        
        @param notificaiton: The notification to adapt
        @type notification: NotificationSubscription
        """
        
    def generateJavascriptContent(notification):
        """
        Generate a block of JS that will be used to render this action's
        content tab in the UI.

        @param notification: The notification providing the data.
        @type notification: NotificationSubscription
        """
    
    def updateContent(content, **kwargs):
        """
        Update the notification's content.

        @param content: This is the NotificationSubscription.content container
                        for this action's data.
        @type content: dict
        @param kwargs: key word arguments passed to the update method. Contains
                       all update params.
        @type kwargs: dict
        """

class IProvidesEmailAddresses(Interface):
    def getEmailAddresses():
        pass

class IProvidesPagerAddresses(Interface):
    def getPagerAddresses():
        pass

class IProcessSignal(Interface):
    """
    @deprecated: Use INotificationContextProvider.
    """

    def process(signal):
        """
        @param signal: The signal that may require additional processing
        @type signal: zenoss.protocols.protobufs.zep_pb2.Signal
        """
        pass

class INotificationContextProvider(Interface):
    """
    Hook to allow a ZenPack to provide additional context to a notification.
    @since 4.1.1
    """

    def updateContext(signal, context):
        """
        @param signal: The signal which triggered the notification.
        @type signal: zenoss.protocols.protobufs.zep_pb2.Signal
        @param context: The dictionary of context passed to the underlying
                        notification.
        @type context: dict
        """

