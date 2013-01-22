##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from datetime import datetime
import logging
import parser
from Acquisition import aq_parent
from zExceptions import BadRequest
from zope.component import getUtility
from zope.component.interfaces import ComponentLookupError
from zope.interface import providedBy

from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import IInfo
from Products.ZenModel.NotificationSubscription import NotificationSubscription
from Products.ZenModel.NotificationSubscriptionWindow import NotificationSubscriptionWindow
from Products.ZenModel.Trigger import Trigger, InvalidTriggerActionType, DuplicateTriggerName
import zenoss.protocols.protobufs.zep_pb2 as zep
from zenoss.protocols.jsonformat import to_dict, from_dict
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier, IGUIDManager
from AccessControl import getSecurityManager

from zenoss.protocols.interfaces import IQueueSchema
from zenoss.protocols.services.triggers import TriggerServiceClient

from Products.ZenModel.ZenossSecurity import (
    MANAGER_ROLE, MANAGE_NOTIFICATION_SUBSCRIPTIONS, MANAGE_TRIGGER,
    NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE, NOTIFICATION_UPDATE_ROLE,
    NOTIFICATION_VIEW_ROLE, OWNER_ROLE, TRIGGER_MANAGER_ROLE,
    TRIGGER_UPDATE_ROLE, TRIGGER_VIEW_ROLE, UPDATE_NOTIFICATION,
    UPDATE_TRIGGER, VIEW_NOTIFICATION, VIEW_TRIGGER,
    ZEN_MANAGER_ROLE,
)

from Products.ZenModel.UserSettings import GroupSettings
from Products.ZenModel.interfaces import IAction
from zope.schema import getFields

log = logging.getLogger('zen.TriggersFacade')


class TriggersFacade(ZuulFacade):

    def __init__(self, context):
        super(TriggersFacade, self).__init__(context)

        self._guidManager = IGUIDManager(self._dmd)

        config = getGlobalConfiguration()
        schema = getUtility(IQueueSchema)
        self.triggers_service = TriggerServiceClient(config.get('zep_uri', 'http://localhost:8084'), schema)

        self.notificationPermissions = NotificationPermissionManager()
        self.triggerPermissions = TriggerPermissionManager()

    def _removeNode(self, obj):
        """
        Remove an object in ZODB.

        This method was created to provide a hook for unit tests.
        """
        context = aq_parent(obj)
        return context._delObject(obj.id)

    def _removeTriggerFromZep(self, uuid):
        """
        Remove a trigger from ZEP.

        This method was created to provide a hook for unit tests.
        """
        return self.triggers_service.removeTrigger(uuid)

    def removeNode(self, uid):
        obj = self._getObject(uid)
        return self._removeNode(obj)

    def _setTriggerGuid(self, trigger, guid):
        """
        @param trigger: The trigger object to set the guid on.
        @type trigger: Products.ZenModel.Trigger.Trigger
        @param guid: The guid
        @type guid: str

        This method was created to provide a hook for unit tests.
        """
        IGlobalIdentifier(trigger).guid = guid

    def _getTriggerGuid(self, trigger):
        """
        @param trigger: The trigger object in zodb.
        @type trigger: Products.ZenModel.Trigger.Trigger

        This method was created to provide a hook for unit tests.
        """
        return IGlobalIdentifier(trigger).guid

    def _setupTriggerPermissions(self, trigger):
        """
        This method was created to provide a hook for unit tests.
        """
        self.triggerPermissions.setupTrigger(trigger)

    def synchronize(self):
        """
        This method will first synchronize all triggers that exist in ZEP to their
        corresponding objects in ZODB. Then, it will clean up notifications and
        remove any subscriptions to triggers that no longer exist.
        """

        log.debug('SYNC: Starting trigger and notification synchronization.')

        _, trigger_set = self.triggers_service.getTriggers()

        zep_uuids = set(t.uuid for t in trigger_set.triggers)
        zodb_triggers = self._getTriggerManager().objectValues()

        # delete all triggers in zodb that do not exist in zep.
        for t in zodb_triggers:
            if not self._getTriggerGuid(t) in zep_uuids:
                log.info('SYNC: Found trigger in zodb that does not exist in zep, removing: %s' % t.id)
                self._removeNode(t)

        zodb_triggers = self._getTriggerManager().objectValues()
        zodb_uuids = set(self._getTriggerGuid(t) for t in zodb_triggers)

        # create all triggers in zodb that do not exist in zep.
        for t in trigger_set.triggers:
            if not t.uuid in zodb_uuids:
                log.info('SYNC: Found trigger uuid in zep that does not seem to exist in zodb, creating: %s' % t.name)
                triggerObject = Trigger(str(t.name))

                try:
                    self._getTriggerManager()._setObject(triggerObject.id, triggerObject)

                except BadRequest:
                    # looks like the id already exists, remove this specific
                    # trigger from zep. This can happen if multiple createTrigger
                    # requests are sent from the browser at once - the transaction
                    # will not abort until after the requests to create a trigger
                    # have already been sent to zep.
                    # See https://dev.zenoss.com/tracint/ticket/28272
                    log.info('SYNC: Found trigger with duplicate id in zodb, deleting from zep: %s (%s)' % (triggerObject.id, t.uuid))
                    self._removeTriggerFromZep(t.uuid)

                else:
                    # setting a guid fires off events, we have to acquire the object
                    # before we adapt it, otherwise adapters responding to the event
                    # will get the 'regular' Trigger object and not be able to handle
                    # it.
                    self._setTriggerGuid(self._getTriggerManager().findChild(triggerObject.id), str(t.uuid))

                    self._setupTriggerPermissions(self._getTriggerManager().findChild(t.name))

        # sync notifications
        for n in self._getNotificationManager().getChildNodes():
            is_changed = False

            subs = list(n.subscriptions)
            for s in subs:
                if s not in zep_uuids:
                    # this trigger no longer exists in zep, remove it from
                    # this notification's subscriptions.
                    log.info('SYNC: Notification subscription no longer valid: %s' % s)
                    is_changed = True
                    n.subscriptions.remove(s)

            if is_changed:
                log.debug('SYNC: Updating notification subscriptions: %s' % n.id)
                self.updateNotificationSubscriptions(n)

        log.debug('SYNC: Trigger and notification synchronization complete.')


    def getTriggers(self):
        self.synchronize()

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
        return self.createTrigger(
            name = newId,
            uuid = None,
            rule = dict(
                source = ''
            )
        )

    def createTrigger(self, name, uuid=None, rule=None):
        name = str(name)

        zodb_triggers = self._getTriggerManager().objectValues()
        zodb_trigger_names = set(t.id for t in zodb_triggers)
        if name in zodb_trigger_names:
            raise DuplicateTriggerName, ('The id "%s" is invalid - it is already in use.' % name)

        triggerObject = Trigger(name)
        self._getTriggerManager()._setObject(name, triggerObject)
        acquired_trigger = self._getTriggerManager().findChild(name)

        if uuid:
            IGlobalIdentifier(acquired_trigger).guid = str(uuid)
        else:
            IGlobalIdentifier(acquired_trigger).create()

        self.triggerPermissions.setupTrigger(acquired_trigger)

        trigger = zep.EventTrigger()
        trigger.uuid = IGlobalIdentifier(acquired_trigger).guid
        trigger.name = name
        trigger.rule.api_version = 1
        trigger.rule.type = zep.RULE_TYPE_JYTHON

        if rule and 'source' in rule:
            trigger.rule.source = rule['source']
        else:
            trigger.rule.source = ''

        self.triggers_service.addTrigger(trigger)

        log.debug('Created trigger with uuid: %s ' % trigger.uuid)
        return trigger.uuid


    def removeTrigger(self, uuid):
        user = getSecurityManager().getUser()
        trigger = self._guidManager.getObject(uuid)

        if self.triggerPermissions.userCanUpdateTrigger(user, trigger):
            # If a user has the ability to update (remove) a trigger, it is
            # presumed that they will be consciously deleting triggers that
            # may have subscribers.
            #
            # Consider that that trigger may be subscribed to by notifications
            # that the current user cannot read/edit.

            # if there was an error, the triggers service will throw an exception
            self._removeTriggerFromZep(uuid)

            context = aq_parent(trigger)
            context._delObject(trigger.id)

            relevant_notifications = self.getNotificationsBySubscription(uuid)

            updated_count = 0
            for n in relevant_notifications:
                n.subscriptions.remove(uuid)
                log.debug('Removing trigger uuid %s from notification: %s' % (uuid, n.id))
                self.updateNotificationSubscriptions(n)
                updated_count += 1

            return updated_count
        else:
            log.warning('User not authorized to remove trigger: User: %s, Trigger: %s' % (user.getId(), trigger.id))
            raise Exception('User not authorized to remove trigger: User: %s, Trigger: %s' % (user.getId(), trigger.id))

    def getNotificationsBySubscription(self, trigger_uuid):
        for n in self._getNotificationManager().getChildNodes():
            if trigger_uuid in n.subscriptions:
                yield n

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

    def getTriggerList(self):
        """
        Retrieve a list of all triggers by uuid and name. This is used by the UI
        to render triggers that a user may not have permission to otherwise view,
        edit or manage.
        """
        response, trigger_set = self.triggers_service.getTriggers()
        trigger_set = to_dict(trigger_set)
        triggerList = []
        if 'triggers' in trigger_set:
            for t in trigger_set['triggers']:
                triggerList.append(dict(
                    uuid = t['uuid'],
                    name = t['name']
                ))
        return sorted(triggerList, key=lambda k: k['name'])

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
            if "name" in data:
                triggerObj.setTitle(data["name"])
            trigger = from_dict(zep.EventTrigger, data)
            response, content = self.triggers_service.updateTrigger(trigger)
            return content



    def _getTriggerManager(self):
        return self._dmd.findChild('Triggers')

    def _getNotificationManager(self):
        return self._dmd.findChild('NotificationSubscriptions')


    def getNotifications(self):
        self.synchronize()

        user = getSecurityManager().getUser()
        for n in self.notificationPermissions.findNotifications(user, self._getNotificationManager().getChildNodes()):
            yield IInfo(n)


    def _updateContent(self, notification, data=None):

        try:
            util = getUtility(IAction, notification.action)
        except ComponentLookupError:
            raise InvalidTriggerActionType("Invalid action type specified: %s" % notification.action)

        fields = {}
        for iface in providedBy(util.getInfo(notification)):
            f = getFields(iface)
            if f:
                fields.update(f)

        data = util.getDefaultData(self._dmd)
        for k, v in fields.iteritems():
            if k not in data:
                data[k] = v.default

        util.updateContent(notification.content, data)

    def addNotification(self, newId, action):
        notification = self.createNotification(newId, action)
        return IInfo(notification)

    def createNotification(self, id, action, guid=None):
        notification = NotificationSubscription(id)
        notification.action = action
        self._updateContent(notification)

        self._getNotificationManager()._setObject(id, notification)

        acquired_notification = self._getNotificationManager().findChild(id)
        self.notificationPermissions.setupNotification(acquired_notification)
        self.updateNotificationSubscriptions(notification)

        notification = self._getNotificationManager().findChild(id)
        notification.userRead = True
        notification.userWrite = True
        notification.userManage = True

        if guid:
            IGlobalIdentifier(notification).guid = guid

        return notification


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

        # can't change action type after creation
        if 'action' in data:
            del data['action']

        notification = self._getObject(uid)

        if not notification:
            raise Exception('Could not find notification to update: %s' % uid)

        # don't update any properties unless the current user has the correct
        # permission.
        user = getSecurityManager().getUser()
        if self.notificationPermissions.userCanUpdateNotification(user, notification):
            # update the action content data
            action = getUtility(IAction, notification.action)
            action.updateContent(notification.content, data)



        if self.notificationPermissions.userCanManageNotification(user, notification):
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

            notification.subscriptions = data.get('subscriptions')
            self.updateNotificationSubscriptions(notification)

            notification.recipients = data.get('recipients', [])
            self.notificationPermissions.clearPermissions(notification)
            self.notificationPermissions.updatePermissions(self._guidManager, notification)

        log.debug('updated notification: %s' % notification)

    def getRecipientOptions(self):
        users = self._dmd.ZenUsers.getAllUserSettings()
        groups = self._dmd.ZenUsers.getAllGroupSettings()

        data = []

        for u in users:
            data.append(self.fetchRecipientOption(u))

        for g in groups:
            data.append(self.fetchRecipientOption(g))
        return data

    def fetchRecipientOption(self, recipient):
        my_type = 'group' if isinstance(recipient, GroupSettings) else 'user'
        return dict(
            type = my_type,
            label = '%s (%s)' % (recipient.getId(), my_type.capitalize()),
            value = IGlobalIdentifier(recipient).getGUID(),
        )

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
                start = start + " T" + data['starttime']
                startDT = datetime.strptime(start, "%m-%d-%Y T%H:%M")
                setattr(window, 'start', int(startDT.strftime('%s')))
            elif field['id'] == 'duration':
                setattr(window, 'duration', int(data['duration']))
            elif field['id'] == 'skip':
                skip = data.get('skip')
                if skip is not None:
                    window.skip = skip
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
        return trigger.globalRead or self.securityManager.checkPermission(VIEW_TRIGGER, trigger)

    def userCanUpdateTrigger(self, user, trigger):
        return trigger.globalWrite or self.securityManager.checkPermission(UPDATE_TRIGGER, trigger)

    def userCanManageTrigger(self, user, trigger):
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
        return notification.globalRead or self.securityManager.checkPermission(VIEW_NOTIFICATION, notification)

    def userCanUpdateNotification(self, user, notification):
        """
        check to see if the current user can update the notification. Take into
        account global settings of the notification, and then just defer a
        permission check to zope.
        """
        return notification.globalWrite or self.securityManager.checkPermission(UPDATE_NOTIFICATION, notification)

    def userCanManageNotification(self, user, notification):
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
        recipientsForRemoval = {}
        for recipient in notification.recipients:
            if recipient['type'] != 'manual':
                userOrGroup = guidManager.getObject(recipient['value'])
                if not userOrGroup:
                    recipientsForRemoval[recipient['value']]= recipient
                    log.info('Recipient %s not found: it may have been deleted. This recipient will be removed from the notification %s.', recipient['label'], notification.id)
                    continue

                notification.manage_addLocalRoles(userOrGroup.id, [NOTIFICATION_VIEW_ROLE])
                log.debug('Added role: %s for user or group: %s' % (NOTIFICATION_VIEW_ROLE, userOrGroup.id))

                log.debug(recipient)

                if recipient.get('write'):
                    notification.manage_addLocalRoles(userOrGroup.id, [NOTIFICATION_UPDATE_ROLE])
                    log.debug('Added role: %s for user or group: %s' % (NOTIFICATION_UPDATE_ROLE, userOrGroup.id))

                if recipient.get('manage'):
                    notification.manage_addLocalRoles(userOrGroup.id, [NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE])
                    log.debug('Added role: %s for user or group: %s' % (NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE, userOrGroup.id))

        notification.recipients = [recip for recip in notification.recipients if recip['value'] not in recipientsForRemoval]


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
