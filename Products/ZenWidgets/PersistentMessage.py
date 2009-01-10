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
__doc__ = """
This is in a separate module to prevent recursive import.
"""

import time
from zope.interface import implements

from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *
from Products.ZenWidgets.interfaces import IMessage
from Products.ZenWidgets.messaging import INFO

class PersistentMessage(ZenModelRM):
    """
    A single message. Messages are stored as relations on UserSettings and in
    the session object.
    """
    implements(IMessage)

    _relations = (("messageQueue", ToOne(
      ToManyCont, "Products.ZenModel.UserSettings.UserSettings", "messageQueue")
    ),)

    title = None
    body = None
    timestamp = None
    priority = None
    _read = False

    def __init__(self, id, title, body, priority=INFO, image=None):
        """
        Initialization method.

        @param title: The message title
        @type title: str
        @param body: The body of the message
        @type body: str
        @param priority: Message priority; one of INFO, WARNING, CRITICAL
        @type priority: int
        @param image: Optional URL of an image to be displayed in the message
        @type image: str
        """
        super(PersistentMessage, self).__init__(id)
        self.title = title
        self.body = body
        self.priority = priority
        self.image = image
        self.timestamp = time.time()

    def mark_as_read(self):
        """
        Mark this message as read.
        """
        self._read = True

    def delete(self):
        """
        Delete this message from the system.
        """
        self.__primary_parent__._delObject(self.id)

