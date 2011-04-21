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
"""
Operations for Messaging.

Available at:  /zport/dmd/messaging_router
"""
from Persistence import PersistentMapping
from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.extdirect.router import DirectResponse
from Products.ZenModel.ZenossSecurity import *
from Products.ZenWidgets.interfaces import IUserMessages, IBrowserMessages
from Products.ZenWidgets import messaging


class MessagingRouter(DirectRouter):
    """
    A JSON/ExtDirect interface to operations on messages
    """
    def setBrowserState(self, state):
        """
        Save the browser state for the current user.

        @param state: The browser state as a JSON-encoded string
        @type state: str
        """
        userSettings = self.context.ZenUsers.getUserSettings()
        state_container = getattr(userSettings, '_browser_state', None)
        if isinstance(state_container, basestring) or state_container is None:
            state_container = PersistentMapping()
            userSettings._browser_state = state_container
        state_container['state'] = state

    def getUserMessages(self):
        """
        Get the queued messages for the logged in user.

        @rtype:   dictionary
        @return:  B{Properties}:
           - messages: ([string]) A list of queued messages.
        """
        # user messages are stored in the logged in users "usersettings" object
        # which must be able to access ZenUsers (off of dmd)
        messages = IUserMessages(self.context.zport.dmd).get_unread()
        messages.extend(IBrowserMessages(self.context).get_unread())
        messages.sort(key=lambda x:x.timestamp)
        result = []
        for message in messages:
            result.append(dict(
                sticky = True if message.priority >= messaging.CRITICAL else False,
                image = message.image,
                title = message.title,
                body = message.body,
                priority = message.priority
            ))
            message.mark_as_read()

        return {
            'messages': result
        }
