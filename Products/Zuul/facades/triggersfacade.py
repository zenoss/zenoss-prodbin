###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.ZenUtils.PkgResources import pkg_resources
from datetime import datetime
import logging
import uuid
import parser
from Acquisition import aq_parent
from zope.interface import implements
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import IInfo
from Products.ZenModel.NotificationSubscription import NotificationSubscription
from Products.ZenModel.NotificationSubscriptionWindow import NotificationSubscriptionWindow
import zenoss.protocols.protobufs.zep_pb2 as zep
from zenoss.protocols.jsonformat import to_dict, from_dict
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.guid.interfaces import IGloballyIdentifiable, IGlobalIdentifier, IGUIDManager

from zenoss.protocols.services.triggers import TriggerServiceClient

log = logging.getLogger('zen.TriggersFacade')


class TriggersFacade(ZuulFacade):
    
    def __init__(self, context):
        super(TriggersFacade, self).__init__(context)
        
        config = getGlobalConfiguration()
        self.triggers_service = TriggerServiceClient(config.get('zep_uri', 'http://localhost:8084'))
    
    def removeNode(self, uid):
        obj = self._getObject(uid)
        context = aq_parent(obj)
        return context._delObject(obj.id)
        
    def getTriggers(self):
        response, trigger_set = self.triggers_service.getTriggers()
        trigger_set = to_dict(trigger_set)
        if 'triggers' in trigger_set:
            return trigger_set['triggers']
        else:
            return []
    
    def parseFilter(self, source):
        """
        Parse a filter to make sure it's sane.
        
        @param source: The python expression to test.
        @type source: string
        @todo: make this not allow nasty python.
        """
        if isinstance(source, basestring):
            if source:
                tree = parser.expr(source)
                if parser.isexpr(tree):
                    return source
                else:
                    raise Exception('Invalid filter expression.')
            else:
                return True # source is empty string
        

    def addTrigger(self, newId):
        trigger = zep.EventTrigger()
        trigger.uuid = str(uuid.uuid4())
        trigger.name = newId
        trigger.rule.api_version = 1
        trigger.rule.type = zep.RULE_TYPE_JYTHON
        trigger.rule.source = ''
        response, content = self.triggers_service.addTrigger(trigger)
        return content

    def removeTrigger(self, uuid):
        response, content = self.triggers_service.removeTrigger(uuid)
        return content

    def getTrigger(self, uuid):
        response, trigger = self.triggers_service.getTrigger(uuid)
        return to_dict(trigger)
    
    def updateTrigger(self, **kwargs):
        trigger = from_dict(zep.EventTrigger, kwargs)
        response, content = self.triggers_service.updateTrigger(trigger)
        return content
    
    
    def _getManager(self):
        return self._dmd.findChild('NotificationSubscriptions')
        
    def getNotifications(self):
        for notification in self._getManager().getChildNodes():
            yield IInfo(notification)
    
    def addNotification(self, newId, action):
        notification = NotificationSubscription(newId)
        notification.action = action
        self._getManager()._setObject(newId, notification)
        
        self.updateNotificationSubscriptions(notification)
        
        return IInfo(self._getManager().findChild(newId))
    
    def removeNotification(self, uid):
        return self.removeNode(uid)
    
    def getNotification(self, uid):
        notification = self._getObject(uid)
        if notification:
            return IInfo(notification)
    
    def updateNotificationSubscriptions(self, notification):
        triggerSubscriptions = []
        notification_guid = IGlobalIdentifier(notification).getGUID()
        for subscription in notification.subscriptions:
            triggerSubscriptions.append(dict(
                delay_seconds = notification.delay_seconds,
                repeat_seconds = notification.repeat_seconds,
                subscriber_uuid = notification_guid,
                trigger_uuid = subscription,
            ));
        subscriptionSet = from_dict(zep.EventTriggerSubscriptionSet, dict(
            subscriptions = triggerSubscriptions
        ))
        
        self.triggers_service.updateSubscriptions(notification_guid, subscriptionSet)

            
    def updateNotification(self, **data):
        log.debug(data)
        
        uid = data['uid']
        
        notification = self._getObject(uid)
        if not notification:
            raise Exception('Could not find notification to update: %s' % uid)
            
        for field in notification._properties:
            setattr(notification, field['id'], data.get(field['id']))
        
        notification.recipients = data.get('recipients')
        
        # editing as a text field, but storing as a list for now.
        notification.subscriptions = [data.get('subscriptions')]
        
        self.updateNotificationSubscriptions(notification)
        
        log.debug('updated notification: %s' % notification)

    def getRecipientOptions(self):
        users = self._dmd.ZenUsers.getAllUserSettings()
        groups = self._dmd.ZenUsers.getAllGroupSettings()
        
        data = []
        
        for u in users:
            data.append(dict(
                type = 'user',
                label = '%s (User)' % u.getId(),
                value = IGlobalIdentifier(u).getGUID()
            ))
        
        for g in groups:
            data.append(dict(
                type = 'group',
                label = '%s (Group)' % g.getId(),
                value = IGlobalIdentifier(g).getGUID()
            ))
        return data
    
    def getWindows(self, uid):
        notification = self._getObject(uid)
        for window in notification.windows():
            yield IInfo(window)
    
    def addWindow(self, contextUid, newId):
        notification = self._getObject(contextUid)
        window = NotificationSubscriptionWindow(newId)
        notification.windows._setObject(newId, window)
        new_window = notification.windows._getOb(newId)
        return IInfo(new_window)
    
    def removeWindow(self, uid):
        return self.removeNode(uid)
    
    def getWindow(self, uid):
        window = self._getObject(uid)
        return IInfo(window)
    
    def updateWindow(self, data):
        uid = data['uid']
        window = self._getObject(uid)
        
        if not window:
            raise Exception('Could not find window to update: %s' % uid)
        for field in window._properties:
            if field['id'] == 'start':
                start = data['start']
                start = start.replace('T00:00:00', 'T' + data['starttime'])
                startDT = datetime.strptime(start, "%Y-%m-%dT%H:%M")
                setattr(window, 'start', startDT.strftime('%s'))
            else:
                setattr(window, field['id'], data.get(field['id']))
        
        log.debug('updated window')

    