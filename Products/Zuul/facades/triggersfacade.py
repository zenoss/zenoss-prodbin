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

import logging
import uuid
from Acquisition import aq_parent
from zope.interface import implements
from zope.component import getUtility
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import ITriggersFacade, IInfo
from Products.ZenModel.NotificationSubscription import NotificationSubscription
from Products.ZenModel.NotificationSubscriptionWindow import NotificationSubscriptionWindow
from Products.ZenMessaging.interfaces import ITriggersService, IProtobufJsonizable
import zenoss.protocols.protobufs.zep_pb2 as zep

log = logging.getLogger('zen.TriggersFacade')


class TriggersFacade(ZuulFacade):
    implements(ITriggersFacade)
    
    def removeNode(self, uid):
        obj = self._getObject(uid)
        context = aq_parent(obj)
        return context._delObject(obj.id)
        
    @property
    def triggers_service(self):
        return getUtility(ITriggersService)
        
    def getTriggers(self):
        trigger_set = self.triggers_service.getTriggers()
        return IProtobufJsonizable(trigger_set).json_friendly()

    def addTrigger(self, newId):
        trigger = zep.EventTrigger()
        trigger.uuid = str(uuid.uuid4())
        trigger.name = newId
        trigger.filter.api_version = 1
        trigger.filter.content_type = 'python'
        trigger.filter.content = ''
        return self.triggers_service.addTrigger(trigger)

    def removeTrigger(self, uuid):
        trigger = zep.EventTrigger()
        trigger.uuid = uuid
        return self.triggers_service.removeTrigger(trigger)

    def getTrigger(self, uuid):
        trigger = self.triggers_service.getTrigger(uuid)
        return IProtobufJsonizable(trigger).json_friendly()
    
    def updateTrigger(self, **kwargs):
        trigger = zep.EventTrigger()
        IProtobufJsonizable(trigger).fill(kwargs)
        return self.triggers_service.updateTrigger(trigger)
    
    def parseFilter(self, source):
        return self.triggers_service.parseFilter(source)
    
    
    
    
    def _getManager(self):
        return self._dmd.findChild('NotificationSubscriptions')
        
    def getNotifications(self):
        # don't think I'm doing this correctly, don't know yet how to manage
        # ownership and what not.
        for notification in self._getManager().getChildNodes():
            yield IInfo(notification)
    
    def addNotification(self, newId):
        notification = NotificationSubscription(newId)
        self._getManager()._setObject(newId, notification)
        return IInfo(self._getManager().findChild(newId))
    
    def removeNotification(self, uid):
        return self.removeNode(uid)
    
    def getNotification(self, uid):
        notification = self._getObject(uid)
        if notification:
            return IInfo(notification)
        
    def updateNotification(self, **data):
        log.debug(data)
        try:
            uid = data['uid']
            del data['uid']
            notification = self._getObject(uid)
            if not notification:
                log.info('Could not find notification to update: %s' % uid)
                return
                
            for field in notification._properties:
                log.debug('setting: %s: %s' % (field['id'], data.get(field['id'])))
                setattr(notification, field['id'], data.get(field['id']))
            
            # editing as a text field, but storing as a list for now.
            notification.subscriptions = [data.get('subscriptions')]
            
            log.debug('updated notification: %s' % notification)
        except KeyError, e:
            log.error('Could not update notification:')
            log.exception(e)
            raise Exception('There was an error updating the notificaton: missing required field.')
    
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
        try:
            uid = data['uid']
            del data['uid']
            window = self._getObject(uid)
            if not window:
                log.info('could not find schedule window to update: %s' % uid)
                return
            
            for field in window._properties:
                log.debug('setting: %s: %s' % (field['id'], data.get(field['id'])))
                setattr(window, field['id'], data.get(field['id']))
            log.debug('updated window')
            
        except KeyError, e:
            log.error('Could not update schedule window:')
            log.exception(e)
            raise Exception('There was an error updating the schedule window: missing required field.')
    