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

import logging
log = logging.getLogger("zen.notifications")
from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from Products.ZenModel.ZenossSecurity import *
from Products.ZenRelations.RelSchema import *
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenUtils.guid.interfaces import IGUIDManager
from zope.interface import implements
from Products.ZenUtils.guid.interfaces import IGloballyIdentifiable
from Products.ZenUtils.template import Template

def manage_addNotificationSubscriptionManager(context, REQUEST=None):
    """Create the notification subscription manager."""
    nsm = NotificationSubscriptionManager(NotificationSubscriptionManager.root)
    context._setObject(NotificationSubscriptionManager.root, nsm)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main')

class NotificationSubscriptionManager(ZenModelRM):
    """Manage notification subscriptions.

    @todo: change the icon parameter in factory_type_information.
    """

    security = ClassSecurityInfo()

    _id = "NotificationSubscriptionManager"
    root = 'NotificationSubscriptions'
    meta_type = _id

    sub_meta_types = ("NotificationSubscription",)

    factory_type_information = (
        {
            'id'             : _id,
            'meta_type'      : _id,
            'description'    : """Management of notification subscriptions""",
            'icon'           : 'UserSettingsManager.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addNotificationSubscriptionManager',
            'immediate_view' : 'editSettings',
            'actions'        : (
                {
                    'id'            : 'settings',
                    'name'          : 'Settings',
                    'action'        : '../editSettings',
                    'permissions'   : ( ZEN_MANAGE_DMD, )
                })
         },
    )


addNotificationSubscription = DTMLFile('dtml/addNotificationSubscription',globals())

def manage_addNotificationSubscription(context, id, title = None, REQUEST = None):
    """Create a notification subscription"""
    ns = NotificationSubscription(id, title)
    context._setObject(id, ns)
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main')

class NotificationSubscription(ZenModelRM):
    """
    A subscription to a signal that produces notifications in the form of
    actions.
    """
    implements(IGloballyIdentifiable)

    _id = "NotificationSubscription"
    meta_type = _id

    enabled = False
    action = 'email'
    send_clear = False
    content_types = ('text', 'html')
    body_content_type = 'html'

    delay_seconds = 0
    repeat_seconds = 0
    action_timeout = 60
    send_initial_occurrence = True

    subject_format = "[zenoss] {event.actor.element_identifier} {event.summary}"
    body_format =  "Device: {event.actor.element_identifier}\n" \
        "Component: {event.actor.element_sub_identifier}\n" \
        "Severity: {event.severity}\n" \
        "Time: {eventSummary.last_seen_time}\n" \
        "Message:\n{event.message}\n" \
        "<a href=\"{event.eventUrl}\">Event Detail</a>\n" \
        "<a href=\"{event.ackUrl}\">Acknowledge</a>\n" \
        "<a href=\"{event.deleteUrl}\">Delete</a>\n" \
        "<a href=\"{event.eventsUrl}\">Device Events</a>\n"

    clear_subject_format = "[zenoss] CLEAR: {event.actor.element_identifier} {event.summary}"
    clear_body_format =  "Event: '{event.summary}'\n" \
        "Cleared by: '{event.cleared_by_event_uuid}'\n" \
        "At: {event.status_change_time}\n" \
        "Device: {event.actor.element_identifier}\n" \
        "Component: {event.actor.element_sub_identifier}\n" \
        "Severity: {event.severity}\n" \
        "Message:\n{event.message}\n" \
        "<a href=\"{event.undeleteUrl}\">Undelete</a>\n"


    # recipients is a list of uuids that will recieve the push from this
    # notification. (the User, Group or Role to email/page/etc.)
    # the uuid objects will need to implement some form of actionable target
    # See IAction classes for more info.
    recipients = []

    # a list of trigger uuids that this notification is subscribed to.
    subscriptions = []

    _properties = ZenModelRM._properties + (
        {'id':'enabled', 'type':'boolean', 'mode':'w'},
        {'id':'send_clear', 'type':'boolean', 'mode':'w'},
        {'id':'send_initial_occurrence', 'type':'boolean', 'mode':'w'},
        {'id':'body_content_type', 'type':'text', 'mode':'w'},
        {'id':'delay_seconds', 'type':'int', 'mode':'w'},
        {'id':'repeat_seconds', 'type':'int', 'mode':'w'},
        {'id':'action_timeout', 'type':'int', 'mode':'w'},
        {'id':'subject_format', 'type':'text', 'mode':'w'},
        {'id':'body_format', 'type':'text', 'mode':'w'},
        {'id':'clear_subject_format', 'type':'text', 'mode':'w'},
        {'id':'clear_body_format', 'type':'text', 'mode':'w'},
    )

    _relations = (
        ("windows",
        ToManyCont(
            ToOne,
            "Products.ZenModel.NotificationSubscriptionWindow",
            "notificationSubscription"
        )),
    )

    factory_type_information = (
        {
            'id'             : _id,
            'meta_type'      : _id,
            'description'    : """Define the notification and the signals to
                which it is subscribed.""",
            # @todo: fix this icon
            'icon'           : 'ActionRule.gif',
            'product'        : 'ZenEvents',
            'factory'        : 'manage_addNotificationSubscription',
            'immediate_view' : 'editNotificationSubscription',
            'actions'        :(
                {
                    'id'            : 'edit',
                    'name'          : 'Edit',
                    'action'        : 'editNotificationSubscription',
                    'permissions'   : (ZEN_CHANGE_ALERTING_RULES,)
                }
            )
         },
    )

    security = ClassSecurityInfo()

    security.declareProtected(ZEN_CHANGE_ALERTING_RULES, 'manage_editNotificationSubscription')
    def manage_editNotificationSubscription(self, REQUEST=None):
        """Update notification subscription properties"""
        return self.zmanage_editProperties(REQUEST)

    def isActive(self):
        """
        Using maintenance windows and `enabled`, determine if this notification
        is active for right now.
        """
        if self.enabled:
            log.debug('Notification is enabled: %s' %  self.id)
            windows = self.windows()
            if windows:
                log.debug('Notification has (%s) windows.' % len(windows))
                for window in windows:
                    if window.isActive():
                        log.debug('Notification has active window: %s' % window.id)
                        return True
                log.debug('Notification has no active windows, it is NOT enabled.')
                return False
            else:
                log.debug('Notification is enabled, but has no windows, it is active.')
                return True
        else:
            log.debug('Notification NOT enabled: %s' %  self.id)
            return False

    def getBody(self, **kwargs):
        return Template(self.body_format).fill(**kwargs)

    def getSubject(self, **kwargs):
        return Template(self.subject_format).fill(**kwargs)

    def getClearBody(self, **kwargs):
        return Template(self.clear_body_format).fill(**kwargs)

    def getClearSubject(self, **kwargs):
        return Template(self.clear_subject_format).fill(**kwargs)

InitializeClass(NotificationSubscriptionManager)
InitializeClass(NotificationSubscription)
