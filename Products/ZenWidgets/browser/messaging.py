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

from Products.Five.browser import BrowserView

from Products.ZenUtils.json import json
from Products.ZenModel.ZenossSecurity import *
from Products.ZenWidgets.interfaces import IUserMessages, IBrowserMessages
from Products.ZenWidgets import messaging

class UserMessages(BrowserView):
    """
    Delivers up user messages for the current user to the client-side
    YAHOO.zenoss.Messenger.
    """
    @json
    def __call__(self):
        messages = IUserMessages(self.context).get_unread()
        messages.extend(IBrowserMessages(self.context).get_unread())
        messages.sort(key=lambda x:x.timestamp)
        result = []
        for message in messages:
            result.append(dict(
                sticky=message.priority>=messaging.CRITICAL and True or False,
                image=message.image,
                title=message.title,
                body=message.body,
                priority=message.priority
            ))
            message.mark_as_read()
        result = {'totalRecords':len(result),
                  'messages':result}
        return result


class DeleteMessage(BrowserView):
    def __call__(self):
        self.context.delete()

