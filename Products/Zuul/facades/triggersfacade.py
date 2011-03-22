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
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier, IGUIDManager
from AccessControl import getSecurityManager

from zenoss.protocols.services.triggers import TriggerServiceClient

from Products.ZenModel.ZenossSecurity import (
    OWNER_ROLE,
    ZEN_MANAGER_ROLE,
    MANAGER_ROLE,
    NOTIFICATION_VIEW_ROLE,
    NOTIFICATION_UPDATE_ROLE,
    NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE,
    VIEW_NOTIFICATION,
    UPDATE_NOTIFICATION,
    MANAGE_NOTIFICATION_SUBSCRIPTIONS
    )

log = logging.getLogger('zen.TriggersFacade')


class TriggersFacade(ZuulFacade):

    def __init__(self, context):
        super(TriggersFacade, self).__init__(context)

        self._guidManager = IGUIDManager(self._dmd)
        
        config = getGlobalConfiguration()
        self.triggers_service = TriggerServiceClient(config.get('zep_uri', 'http://localhost:8084'))

        self.notificationPermissions = NotificationPermissionManager()

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
        return trigger.uuid

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
        user = getSecurityManager().getUser()
        for n in self.notificationPermissions.findNotifications(user, self._getManager().getChildNodes()):
            n.userRead = True
            n.userWrite = self.notificationPermissions.userCanUpdateNotification(user, n)
            n.userManageSubscriptions = self.notificationPermissions.userCanManageNotification(user, n)
            log.debug(n)
            yield IInfo(n)

    def addNotification(self, newId, action):
        notification = NotificationSubscription(newId)
        notification.action = action

        self._getManager()._setObject(newId, notification)

        acquired_notification = self._getManager().findChild(newId)
        self.notificationPermissions.setupNotification(acquired_notification)

        self.updateNotificationSubscriptions(notification)

        return IInfo(self._getManager().findChild(newId))

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

        # if these values are not sent (in the case that the fields have been
        # disabled, do not set the value.
        if 'notification_globalRead' in data:
            notification.globalRead = data.get('notification_globalRead', False)
            log.debug('setting globalRead')

        if 'notification_globalWrite' in data:
            notification.globalWrite = data.get('notification_globalWrite', False)
            log.debug('setting globalWrite')

        if 'notification_globalManageSubscriptions' in data:
            notification.globalManageSubscriptions = data.get('notification_globalManageSubscriptions', False)
            log.debug('setting globalManageSubscriptions')

        # don't update any properties unless the current user has the correct
        # permission.
        user = getSecurityManager().getUser()
        if self.notificationPermissions.userCanUpdateNotification(user, notification):
            for field in notification._properties:
                notification._updateProperty(field['id'], data.get(field['id']))

            # editing as a text field, but storing as a list for now.
            notification.subscriptions = [data.get('subscriptions')]

            self.updateNotificationSubscriptions(notification)


        # don't allow updating of the recipients properties unless the current
        # user has the correct permission.
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
        return notification.globalManageSubscriptions or self.securityManager.checkPermission(MANAGE_NOTIFICATION_SUBSCRIPTIONS, notification)


    def findNotifications(self, user, notifications):
        """
        Find all notifications that the current user at least has the 'View'
        permission on.
        """
        for notification in notifications:
            if self.userCanViewNotification(user, notification):
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