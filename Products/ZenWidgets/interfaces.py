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

from zope.interface import Interface, Attribute
from zope.app.container.interfaces import IContained, IContainer


class IMessage(IContained):
    """
    A single message. Messages are stored in user-specific MessageQueue objects
    and in the session object.
    """
    title = Attribute("Title of the message")
    body = Attribute("Body of the message")
    image = Attribute("Optional path to image to be displayed")
    priority = Attribute("Priority of the message")
    timestamp = Attribute("Time the message was sent")

    def delete():
        """
        Delete this message from any queues in which it exists.
        """
    def mark_as_read():
        """
        Mark this message as read.
        """


class IMessageSender(Interface):
    """
    Something able to send messages.
    """
    def sendToBrowser(title, body, priority, image):
        """
        Create a message and store it on the request object.
        """
    def sendToUser(title, body, priority, image, user):
        """
        Create a message and store it in the L{IMessageQueue} of the user
        specified. If no user is specified, use the queue of the current user.
        """
    def sendToAll(title, body, priority, image):
        """
        For eash user in the system, create an identical message and store it
        in the user's L{IMessageQueue}.
        """


class IMessageQueue(IContainer):
    """
    Marker interface for a message container.
    """


class IMessageBox(Interface):
    """
    Something that can provide messages.
    """
    messagebox = Attribute("The source of IMessage objects.")
    def get_messages():
        """
        Return all messages.
        """
    def get_unread():
        """
        Return all messages that have not been marked as read.
        """


class IUserMessages(IMessageBox):
    """
    Object that is able to provide IMessage objects from a user queue.
    """


class IBrowserMessages(IMessageBox):
    """
    Object that is able to provide IMessage objects from the request.
    """

