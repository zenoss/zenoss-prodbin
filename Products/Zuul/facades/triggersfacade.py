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
from Products.ZenModel.Trigger import Trigger
import zenoss.protocols.protobufs.zep_pb2 as zep
from zenoss.protocols.jsonformat import to_dict, from_dict
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier, IGUIDManager
from AccessControl import getSecurityManager

from zenoss.protocols.services.triggers import TriggerServiceClient

from Products.ZenModel.ZenossSecurity import *

log = logging.getLogger('zen.TriggersFacade')


class TriggersFacade(ZuulFacade):

    def __init__(self, context):
        super(TriggersFacade, self).__init__(context)

        self._guidManager = IGUIDManager(self._dmd)
        
        config = getGlobalConfiguration()
        self.triggers_service = TriggerServiceClient(config.get('zep_uri', 'http://localhost:8084'))

        self.notificationPermissions = NotificationPermissionManager()
        self.triggerPermissions = TriggerPermissionManager()

    def removeNode(self, uid):
        obj = self._getObject(uid)
        context = aq_parent(obj)
        return context._delObject(obj.id)

    def getTriggers(self):
        user = getSecurityManager().getUser()
        response, trigger_set = self.triggers_service.getTriggers()
        trigger_set = to_dict(trigger_set)
        if 'triggers' in trigger_set:
            return self.triggerPermissions.findTriggers(user, self._guidManager, trigger_set['triggers'])
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
        triggerObject = Trigger(newId)
        self._getTriggerManager()._setObject(newId, triggerObject)
        acquired_trigger = self._getTriggerManager().findChild(newId)
        self.triggerPermissions.setupTrigger(acquired_trigger)

        trigger = zep.EventTrigger()
        trigger.uuid = str(IGlobalIdentifier(acquired_trigger).create())
        trigger.name = newId
        trigger.rule.api_version = 1
        trigger.rule.type = zep.RULE_TYPE_JYTHON
        trigger.rule.source = ''
        response, content = self.triggers_service.addTrigger(trigger)

        log.debug('Created trigger with uuid: %s ' % trigger.uuid)
        return trigger.uuid

    def removeTrigger(self, uuid):
        user = getSecurityManager().getUser()
        trigger = self._guidManager.getObject(uuid)
        
        if self.triggerPermissions.userCanUpdateTrigger(user, trigger):
            response, content = self.triggers_service.removeTrigger(uuid)
            context = aq_parent(trigger)
            context._delObject(trigger.id)
            return content
        else:
            log.warning('User not authorized to remove trigger: User: %s, Trigger: %s' % (user.getId(), trigger.id))
            raise Exception('User not authorized to remove trigger: User: %s, Trigger: %s' % (user.getId(), trigger.id))


    def getTrigger(self, uuid):
        user = getSecurityManager().getUser()
        trigger = self._guidManager.getObject(uuid)
        log.debug('Trying to fetch trigger: %s' % trigger.id)
        if self.triggerPermissions.userCanViewTrigger(user, trigger):
            response, trigger = self.triggers_service.getTrigger(uuid)
            return to_dict(trigger)
        else:
            log.warning('User not authorized to view this trigger: %s' % trigger.id)
            raise Exception('User not authorized to view this trigger: %s' % trigger.id)


    def updateTrigger(self, **data):
        user = getSecurityManager().getUser()
        
        triggerObj = self._guidManager.getObject(data['uuid'])
        
        log.debug('Trying to update trigger: %s' % triggerObj.id)

        if self.triggerPermissions.userCanManageTrigger(user, triggerObj):
            if 'globalRead' in data:
                triggerObj.globalRead = data.get('globalRead', False)
                log.debug('setting globalRead %s' % triggerObj.globalRead)

            if 'globalWrite' in data:
                triggerObj.globalWrite = data.get('globalWrite', False)
                log.debug('setting globalWrite %s' % triggerObj.globalWrite)

            if 'globalManage' in data:
                triggerObj.globalManage = data.get('globalManage', False)
                log.debug('setting globalManage %s' % triggerObj.globalManage)

            triggerObj.users = data.get('users', [])
            self.triggerPermissions.clearPermissions(triggerObj)
            self.triggerPermissions.updatePermissions(self._guidManager, triggerObj)
            
        if self.triggerPermissions.userCanUpdateTrigger(user, triggerObj):
            trigger = from_dict(zep.EventTrigger, data)
            response, content = self.triggers_service.updateTrigger(trigger)
            return content



    def _getTriggerManager(self):
        return self._dmd.findChild('Triggers')

    def _getNotificationManager(self):
        return self._dmd.findChild('NotificationSubscriptions')


    def getNotifications(self):
        user = getSecurityManager().getUser()
        for n in self.notificationPermissions.findNotifications(user, self._getNotificationManager().getChildNodes()):
            yield IInfo(n)

    def addNotification(self, newId, action):
        notification = NotificationSubscription(newId)
        notification.action = action

        self._getNotificationManager()._setObject(newId, notification)

        acquired_notification = self._getNotificationManager().findChild(newId)
        self.notificationPermissions.setupNotification(acquired_notification)

        self.updateNotificationSubscriptions(notification)

        notification = self._getNotificationManager().findChild(newId)
        notification.userRead = True
        notification.userWrite = True
        notification.userManage = True
        return IInfo(notification)

    def removeNotification(self, uid):
        user = getSecurityManager().getUser()
        notification = self._getObject(uid)
        if self.notificationPermissions.userCanUpdateNotification(user, notification):
            return self.removeNode(uid)
        else:
            log.warning('User not authorized to remove notification: User: %s, Notification: %s' % (user.getId(), notification.id))
            raise Exception('User not authorized to remove notification.')

    def getNotification(self, uid):
        user = getSecurityManager().getUser()
        notification = self._getObject(uid)
        if self.notificationPermissions.userCanViewNotification(user, notification):
            log.debug('getting notification: %s' % notification)
            return IInfo(notification)
        else:
            log.warning('User not authorized to view this notification: %s' % uid)
            raise Exception('User not authorized to view this notification: %s' % uid)

    def updateNotificationSubscriptions(self, notification):
        triggerSubscriptions = []
        notification_guid = IGlobalIdentifier(notification).getGUID()
        for subscription in notification.subscriptions:
            triggerSubscriptions.append(dict(
                delay_seconds = notification.delay_seconds,
                repeat_seconds = notification.repeat_seconds,
                subscriber_uuid = notification_guid,
                send_initial_occurrence = notification.send_initial_occurrence,
                trigger_uuid = subscription,
            ))
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

        # don't update any properties unless the current user has the correct
        # permission.
        user = getSecurityManager().getUser()
        if self.notificationPermissions.userCanUpdateNotification(user, notification):
            # if these values are not sent (in the case that the fields have been
            # disabled, do not set the value.
            if 'notification_globalRead' in data:
                notification.globalRead = data.get('notification_globalRead')
                log.debug('setting globalRead')

            if 'notification_globalWrite' in data:
                notification.globalWrite = data.get('notification_globalWrite')
                log.debug('setting globalWrite')

            if 'notification_globalManage' in data:
                notification.globalManage = data.get('notification_globalManage')
                log.debug('setting globalManage')

            for field in notification._properties:
                notification._updateProperty(field['id'], data.get(field['id']))

            # editing as a text field, but storing as a list for now.
            notification.subscriptions = [data.get('subscriptions')]
            self.updateNotificationSubscriptions(notification)

        
        if self.notificationPermissions.userCanManageNotification(user, notification):
            notification.recipients = data.get('recipients', [])
            self.notificationPermissions.clearPermissions(notification)
            self.notificationPermissions.updatePermissions(self._guidManager, notification)

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


class TriggerPermissionManager(object):
    """
    This object helps manage permissions with regard to a trigger. Triggers are
    only stored in the zodb for managing permissions, all of the data associated
    with a trigger is stored externally in ZEP.
    """

    def __init__(self):
        self.securityManager = getSecurityManager()

    def userCanViewTrigger(self, user, trigger):
        log.debug('Checking user "%s" can view trigger "%s": %s' % (
            user.getId(),
            trigger.id,
            self.securityManager.checkPermission(VIEW_TRIGGER, trigger)
        ))
        return trigger.globalRead or self.securityManager.checkPermission(VIEW_TRIGGER, trigger)

    def userCanUpdateTrigger(self, user, trigger):
        log.debug('Checking user "%s" can update trigger "%s": %s' % (
            user.getId(),
            trigger.id,
            self.securityManager.checkPermission(UPDATE_TRIGGER, trigger)
        ))
        return trigger.globalWrite or self.securityManager.checkPermission(UPDATE_TRIGGER, trigger)

    def userCanManageTrigger(self, user, trigger):
        log.debug('Checking user "%s" for managing trigger "%s": %s' % (
            user.getId(),
            trigger.id,
            self.securityManager.checkPermission(MANAGE_TRIGGER, trigger)
        ))
        log.debug('user can manage trigger: %s, %s, %s' % (trigger.id, trigger.globalManage, self.securityManager.checkPermission(MANAGE_TRIGGER, trigger)))
        return trigger.globalManage or self.securityManager.checkPermission(MANAGE_TRIGGER, trigger)

    def findTriggers(self, user, guidManager, triggers):
        results = []
        for trigger in triggers:
            triggerObject = guidManager.getObject(trigger['uuid'])
            if triggerObject and self.userCanViewTrigger(user, triggerObject):

                # copy these properties that are stored on the dmd object to the
                # json-friendly object that is getting passed to the UI
                trigger['globalRead'] = triggerObject.globalRead
                trigger['globalWrite'] = triggerObject.globalWrite
                trigger['globalManage'] = triggerObject.globalManage

                trigger['userRead'] = True
                trigger['userWrite'] = self.userCanUpdateTrigger(user, triggerObject)
                trigger['userManage'] = self.userCanManageTrigger(user, triggerObject)

                trigger['users'] = triggerObject.users
                
                results.append(trigger)
            else:
                log.warning('Could not find trigger for permissions check: %r' % trigger)
        return results

    def clearPermissions(self, trigger):
        # remove all previous local roles, besides 'Owner'
        removeUserIds = []
        for userId, roles in trigger.get_local_roles():
            if OWNER_ROLE not in roles:
                removeUserIds.append(userId)
        log.debug('Removing all local roles for users: %s' % removeUserIds)
        trigger.manage_delLocalRoles(removeUserIds)

    def updatePermissions(self, guidManager, trigger):
       # then add local roles back for all the users/groups that we just added
        for user_info in trigger.users:
            log.debug(user_info)
            if user_info['type'] != 'manual':
                userOrGroup = guidManager.getObject(user_info['value'])

                trigger.manage_addLocalRoles(userOrGroup.id, [TRIGGER_VIEW_ROLE])
                log.debug('Added role: %s for user or group: %s' % (TRIGGER_VIEW_ROLE, userOrGroup.id))


                if user_info.get('write'):
                    trigger.manage_addLocalRoles(userOrGroup.id, [TRIGGER_UPDATE_ROLE])
                    log.debug('Added role: %s for user or group: %s' % (TRIGGER_UPDATE_ROLE, userOrGroup.id))

                if user_info.get('manage'):
                    trigger.manage_addLocalRoles(userOrGroup.id, [TRIGGER_MANAGER_ROLE])
                    log.debug('Added role: %s for user or group: %s' % (TRIGGER_MANAGER_ROLE, userOrGroup.id))


    def setupTrigger(self, trigger):
        # Permissions are managed here because managing these default permissions
        # on the class was not preventing the permissions from being acquired
        # elsewhere.
        trigger.manage_permission(
            VIEW_TRIGGER,
            (OWNER_ROLE,
             MANAGER_ROLE,
             ZEN_MANAGER_ROLE,
             TRIGGER_VIEW_ROLE,
             TRIGGER_UPDATE_ROLE,
             TRIGGER_MANAGER_ROLE),
            acquire=False
        )

        trigger.manage_permission(
            UPDATE_TRIGGER,
            (OWNER_ROLE,
             MANAGER_ROLE,
             ZEN_MANAGER_ROLE,
             TRIGGER_UPDATE_ROLE),
            acquire=False
        )

        trigger.manage_permission(
            MANAGE_TRIGGER,
            (OWNER_ROLE,
             MANAGER_ROLE,
             ZEN_MANAGER_ROLE,
             TRIGGER_MANAGER_ROLE),
            acquire=False
        )
        

class NotificationPermissionManager(object):
    """
    This object helps manage permissions with regard to a notification.
    """

    def __init__(self):
        self.securityManager = getSecurityManager()


    def userCanViewNotification(self, user, notification):
        """
        Check to see if the current user can view this notification. Take into
        account global settings of the notification, and then just defer a
        permission check to zope.
        """
        log.debug('Checking user "%s" can view notification "%s": %s' % (
            user.getId(),
            notification.id,
            self.securityManager.checkPermission(VIEW_NOTIFICATION, notification)
        ))
        return notification.globalRead or self.securityManager.checkPermission(VIEW_NOTIFICATION, notification)

    def userCanUpdateNotification(self, user, notification):
        """
        check to see if the current user can update the notification. Take into
        account global settings of the notification, and then just defer a
        permission check to zope.
        """
        log.debug('Checking user "%s" can update notification "%s": %s' % (
            user.getId(),
            notification.id,
            self.securityManager.checkPermission(UPDATE_NOTIFICATION, notification)
        ))
        return notification.globalWrite or self.securityManager.checkPermission(UPDATE_NOTIFICATION, notification)

    def userCanManageNotification(self, user, notification):
        log.debug('Checking user "%s" for managing notification "%s": %s' % (
            user.getId(),
            notification.id,
            self.securityManager.checkPermission(MANAGE_NOTIFICATION_SUBSCRIPTIONS, notification)
        ))
        return notification.globalManage or self.securityManager.checkPermission(MANAGE_NOTIFICATION_SUBSCRIPTIONS, notification)


    def findNotifications(self, user, notifications):
        """
        Find all notifications that the current user at least has the 'View'
        permission on.
        """
        for notification in notifications:
            if self.userCanViewNotification(user, notification):
                notification.userRead = True
                notification.userWrite = self.userCanUpdateNotification(user, notification)
                notification.userManage = self.userCanManageNotification(user, notification)
                yield notification

    def clearPermissions(self, notification):    
        # remove all previous local roles, besides 'Owner'
        removeUserIds = []
        for userId, roles in notification.get_local_roles():
            if OWNER_ROLE not in roles:
                removeUserIds.append(userId)
        log.debug('Removing all local roles for users: %s' % removeUserIds)
        notification.manage_delLocalRoles(removeUserIds)

    def updatePermissions(self, guidManager, notification):
       # then add local roles back for all the users/groups that we just added
        for recipient in notification.recipients:
            if recipient['type'] != 'manual':
                userOrGroup = guidManager.getObject(recipient['value'])

                notification.manage_addLocalRoles(userOrGroup.id, [NOTIFICATION_VIEW_ROLE])
                log.debug('Added role: %s for user or group: %s' % (NOTIFICATION_VIEW_ROLE, userOrGroup.id))

                log.debug(recipient);

                if recipient.get('write'):
                    notification.manage_addLocalRoles(userOrGroup.id, [NOTIFICATION_UPDATE_ROLE])
                    log.debug('Added role: %s for user or group: %s' % (NOTIFICATION_UPDATE_ROLE, userOrGroup.id))

                if recipient.get('manage_subscriptions'):
                    notification.manage_addLocalRoles(userOrGroup.id, [NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE])
                    log.debug('Added role: %s for user or group: %s' % (NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE, userOrGroup.id))


    def setupNotification(self, notification):
        # Permissions are managed here because managing these default permissions
        # on the class was not preventing the permissions from being acquired
        # elsewhere.
        notification.manage_permission(
            VIEW_NOTIFICATION,
            (OWNER_ROLE,
             MANAGER_ROLE,
             ZEN_MANAGER_ROLE,
             NOTIFICATION_VIEW_ROLE,
             NOTIFICATION_UPDATE_ROLE,
             NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE),
            acquire=False
        )

        notification.manage_permission(
            UPDATE_NOTIFICATION,
            (OWNER_ROLE,
             MANAGER_ROLE,
             ZEN_MANAGER_ROLE,
             NOTIFICATION_UPDATE_ROLE),
            acquire=False
        )

        notification.manage_permission(
            MANAGE_NOTIFICATION_SUBSCRIPTIONS,
            (OWNER_ROLE,
             MANAGER_ROLE,
             ZEN_MANAGER_ROLE,
             NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE),
            acquire=False
        )