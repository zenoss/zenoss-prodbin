###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import os
import Zope2
CONF_FILE = os.path.join(os.environ['ZENHOME'], 'etc', 'zope.conf')
Zope2.configure(CONF_FILE)

import unittest
import Globals
from uuid import uuid4
import logging

log = logging.getLogger('signalProcessorTest')

from zenoss.protocols.protobufs.zep_pb2 import Signal
from Products.ZenEvents.zenactiond import ProcessSignalTask, NotificationDao, TargetableAction
from Products.ZenModel.NotificationSubscription import NotificationSubscription
from Products.ZenTestCase.BaseTestCase import BaseTestCase


class MockNotificationSubscription(NotificationSubscription):
    def __init__(self, id):
        self.id = id
    def windows(self):
        """
        There are no maintenance windows for this mock object.
        """
        return []


trigger_uuid = str(uuid4())
subscriber_uuid = str(uuid4())

test_signal1 = Signal()
test_signal1.uuid = str(uuid4())
test_signal1.created_time = 1;
test_signal1.message = 'Testing Signal Processing'
test_signal1.trigger_uuid = trigger_uuid
test_signal1.subscriber_uuid = subscriber_uuid

manual_recipient = {
    'type':'manual',
    'label':'manual recipient',
    'value':'manual_recipient@example.com'
}

manual_page_recipient = {
    'type':'manual',
    'label':'manual page recipient',
    'value':'555-555-1234'
}

# All of these mock notifications have their uuid set to the same
# subscriber_uuid. This is to ensure that they all match the test signal.
active_email_notification = MockNotificationSubscription('active_email_notification')
active_email_notification.guid = subscriber_uuid
active_email_notification.enabled = True
active_email_notification.recipients = [manual_recipient]
active_email_notification.subscriptions = [trigger_uuid]
active_email_notification.action = 'email'

active_page_notification = MockNotificationSubscription('active_page_notification')
active_page_notification.guid = subscriber_uuid
active_page_notification.enabled = True
active_page_notification.recipients = [manual_page_recipient]
active_page_notification.subscriptions = [trigger_uuid]
active_page_notification.action = 'page'

active_notification_zero = MockNotificationSubscription('active_notification_zero')
active_notification_zero.guid = subscriber_uuid
active_notification_zero.recipients = []
active_notification_zero.subscriptions = [trigger_uuid]
active_notification_zero.action = 'email'

disabled_notification = MockNotificationSubscription('disabled_notification')
disabled_notification.guid = subscriber_uuid
disabled_notification.enabled = False
disabled_notification.recipients = [manual_recipient]
disabled_notification.subscriptions = [trigger_uuid]
disabled_notification.action = 'email'


class MockNotificationDao(NotificationDao):
    """
    This mock object only fakes the notification objects to compare to, it does
    not override any checking functionality. The data source in this mock is
    local instead of fetched from the dmd.
    """
    notifications = []
    def __init__(self):
        pass

    def getNotifications(self):
        return self.notifications

    def notificationSubscribesToSignal(self, notification, signal):
        return signal.subscriber_uuid == notification.guid

class MockAction(TargetableAction):
    """
    This mock action does not perform any action, just records the targets to
    which it would have acted.
    """
    def __init__(self):
        self.result = []

    def getTargets(self, notification):
        return notification.recipients

    def executeOnTarget(self, notification, signal, target):
        # don't actually do anything, just save the target to a list so we
        # can test who would have recieved this notification/action.
        self.result.append(target['value'])

class ProcessSignalTaskTest(BaseTestCase):

    def setUp(self):
        self.mockDao = MockNotificationDao()
        self.taskProcessor = ProcessSignalTask(self.mockDao)

        self.emailAction = MockAction()
        self.pageAction = MockAction()

        self.taskProcessor.registerAction('email', self.emailAction)
        self.taskProcessor.registerAction('page', self.pageAction)

    def testEnabledNotification(self):
        """
        Test that a notification subscription matches a signal and that the
        action for the notification executes.
        """

        self.mockDao.notifications = [active_email_notification]
        self.taskProcessor.processSignal(test_signal1)

        expected_recipients = list(set(
            [recipient['value'] for recipient in active_email_notification.recipients]
        ))
        assert self.emailAction.result == expected_recipients

    def testEnabledNotificationPage(self):
        self.mockDao.notifications = [active_page_notification]
        self.taskProcessor.processSignal(test_signal1)
        expected_recipients = list(set(
            [recipient['value'] for recipient in active_page_notification.recipients]
        ))
        assert self.pageAction.result == expected_recipients

    def testDisabledNotification(self):
        """
        Test that a disabled notification does not execute any actions.
        """
        self.mockDao.notifications = [disabled_notification]
        self.taskProcessor.processSignal(test_signal1)

        assert self.emailAction.result == []

    def testWithoutRecipients(self):
        """
        Test that nothing happens gracefully when a notificaiton does not have
        any recipients.
        """
        self.mockDao.notifications = [active_notification_zero]
        self.taskProcessor.processSignal(test_signal1)

        assert self.emailAction.result == []

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(ProcessSignalTaskTest))
    return suite
