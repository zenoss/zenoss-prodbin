from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.extdirect.router import DirectResponse
from Products.ZenModel.ZenossSecurity import *
from Products.ZenWidgets.interfaces import IUserMessages, IBrowserMessages
from Products.ZenWidgets import messaging

class MessagingRouter(DirectRouter):
    def __init__(self, context, request):
        super(MessagingRouter, self).__init__(context, request)

    def getUserMessages(self):
        messages = IUserMessages(self.context).get_unread()
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