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

import Globals
from traceback import format_exc
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.Utils import formatdate
from twisted.internet import reactor, defer

from zenoss.protocols.queueschema import SchemaException
from zenoss.protocols import hydrateQueueMessage
from zenoss.protocols.interfaces import IQueueSchema
from Products.ZenCallHome.transport.cycler import CallHomeCycler
from Products.ZenCollector.utils.maintenance import MaintenanceCycle, maintenanceBuildOptions, QueueHeartbeatSender
from Products.ZenCollector.utils.workers import ProcessWorkers, workersBuildOptions, exec_worker

from Products.ZenEvents.Schedule import Schedule
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.Utils import getDefaultZopeUrl
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.ZenUtils.guid.guid import GUIDManager

from Products.ZenModel.NotificationSubscription import NotificationSubscriptionManager
from Products.ZenModel.actions import ActionMissingException, TargetableAction, ActionExecutionException
from Products.ZenModel.interfaces import IAction
from Products.ZenEvents.Event import Event
from Products.ZenMessaging.queuemessaging.QueueConsumer import QueueConsumer
from Products.ZenMessaging.queuemessaging.interfaces import IQueueConsumerTask
from Products.ZenEvents.ZenEventClasses import Warning as SEV_WARNING
from zope.component import getUtility, getUtilitiesFor
from zope.component.interfaces import ComponentLookupError
from zope.interface import implements


import logging
log = logging.getLogger("zen.zenactiond")


DEFAULT_MONITOR = "localhost"


class NotificationDao(object):
    def __init__(self, dmd):
        self.dmd = dmd
        self.notification_manager = self.dmd.getDmdRoot(NotificationSubscriptionManager.root)
        self.guidManager = GUIDManager(dmd)

    def getNotifications(self):
        self.dmd._p_jar.sync()
        return self.notification_manager.getChildNodes()

    def getSignalNotifications(self, signal):
        """
        Given a signal, find which notifications match this signal. In order to
        match, a notification must be active (enabled and if has maintenance
        windows, at least one must be active) and must be subscribed to the
        signal.

        @param signal: The signal for which to get subscribers.
        @type signal: protobuf zep.Signal
        """
        active_matching_notifications = []
        for notification in self.getNotifications():
            if notification.isActive():
                if self.notificationSubscribesToSignal(notification, signal):
                    active_matching_notifications.append(notification)
                    log.debug('Found matching notification: %s' % notification)
                else:
                    log.debug('Notification "%s" does not subscribe to this signal.' % notification)
            else:
                log.debug('Notification "%s" is not active.' % notification)

        return active_matching_notifications

    def notificationSubscribesToSignal(self, notification, signal):
        """
        Determine if the notification matches the specified signal.

        @param notification: The notification to check
        @type notification: NotificationSubscription
        @param signal: The signal to match.
        @type signal: zenoss.protocols.protbufs.zep_pb2.Signal

        @rtype boolean
        """
        return signal.subscriber_uuid == IGlobalIdentifier(notification).getGUID()

class ProcessSignalTask(object):
    implements(IQueueConsumerTask)

    def __init__(self, notificationDao):
        self.notificationDao = notificationDao

        # set by the constructor of queueConsumer
        self.queueConsumer = None

        self.schema = getUtility(IQueueSchema)
        self.queue = self.schema.getQueue("$Signals")

    def getAction(self, action):
        try:
            return getUtility(IAction, action)
        except ComponentLookupError, e:
            raise ActionMissingException(action)

    def processMessage(self, message):
        """
        Handles a queue message, can call "acknowledge" on the Queue Consumer
        class when it is done with the message
        """
        log.debug('processing message.')

        if message.content.body == self.queueConsumer.MARKER:
            log.info("Received MARKER sentinel, exiting message loop")
            self.queueConsumer.acknowledge(message)
            return
        try:
            signal = hydrateQueueMessage(message, self.schema)
            self.processSignal(signal)
            log.debug('Done processing signal.')
        except SchemaException:
            log.error("Unable to hydrate protobuf %s. " % message.content.body)
            self.queueConsumer.acknowledge(message)
        except Exception, e:
            log.exception(e)
            # FIXME: Send to an error queue instead of acknowledge.
            log.error('Acknowledging broken message.')
            self.queueConsumer.acknowledge(message)
        else:
            log.debug('Acknowledging message. (%s)' % signal.message)
            self.queueConsumer.acknowledge(message)

    def processSignal(self, signal):
        matches = self.notificationDao.getSignalNotifications(signal)
        log.debug('Found these matching notifications: %s' % matches)

        trigger = self.notificationDao.guidManager.getObject(signal.trigger_uuid)
        audit_event_trigger_info = "Event:'%s' Trigger:%s" % (
                                        signal.event.occurrence[0].fingerprint,
                                        trigger.id)
        for notification in matches:
            if signal.clear and not notification.send_clear:
                log.debug('Ignoring clearing signal since send_clear is set to False on this subscription %s' % notification.id)
                continue
            try:
                target = signal.subscriber_uuid or '<none>'
                action = self.getAction(notification.action)
                action.setupAction(notification.dmd)
                if isinstance(action, TargetableAction):
                    target = ','.join(action.getTargets(notification))
                action.execute(notification, signal)
            except ActionMissingException, e:
                log.error('Error finding action: {action}'.format(action = notification.action))
                audit_msg =  "%s Action:%s Status:%s Target:%s Info:%s" % (
                                    audit_event_trigger_info, notification.action, "FAIL", target, "<action not found>")
            except ActionExecutionException, aee:
                log.error('Error executing action: {action} on notification {notification}'.format(
                    action = notification.action,
                    notification = notification.id,
                ))
                audit_msg =  "%s Action:%s Status:%s Target:%s Info:%s" % (
                                    audit_event_trigger_info, notification.action, "FAIL", target, aee)
            except Exception, e:
                msg = 'Error executing action {notification}'.format(
                    notification = notification.id,
                )
                log.exception(e)
                log.error(msg)
                traceback = format_exc()
                event = Event(device="localhost",
                              eventClass="/App/Failed",
                              summary=msg,
                              message=traceback,
                              severity=SEV_WARNING, component="zenactiond")
                self.dmd.ZenEventManager.sendEvent(event)
                audit_msg =  "%s Action:%s Status:%s Target:%s Info:%s" % (
                                    audit_event_trigger_info, notification.action, "FAIL", target, action.getInfo(notification))
            else:
                # audit trail of performed actions
                audit_msg =  "%s Action:%s Status:%s Target:%s Info:%s" % (
                                    audit_event_trigger_info, notification.action, "SUCCESS", target, action.getInfo(notification))
            log.info(audit_msg)
        log.debug('Done processing signal. (%s)' % signal.message)

class ZenActionD(ZCmdBase):
    def __init__(self):
        super(ZenActionD, self).__init__()
        self._consumer = None
        self._workers = ProcessWorkers(self.options.workers - 1,
                                       exec_worker,
                                       "zenactiond worker")
        self._heartbeatSender = QueueHeartbeatSender('localhost',
                                                 'zenactiond',
                                                 self.options.maintenancecycle *3)

        self._maintenanceCycle = MaintenanceCycle(self.options.maintenancecycle,
                                                  self._heartbeatSender)
        self._callHomeCycler = CallHomeCycler(self.dmd)
        self._schedule = Schedule(self.options, self.dmd)
        self._schedule.sendEvent = self.dmd.ZenEventManager.sendEvent
        self._schedule.monitor = self.options.monitor

    def buildOptions(self):
        super(ZenActionD, self).buildOptions()
        maintenanceBuildOptions(self.parser)
        workersBuildOptions(self.parser, 1)

        default_max_commands = 10
        self.parser.add_option('--maxcommands', dest="maxCommands", type="int", default=default_max_commands,
                               help='Max number of action commands to perform concurrently (default: %d)' % \
                                    default_max_commands)
        default_url = getDefaultZopeUrl()
        self.parser.add_option('--zopeurl', dest='zopeurl', default=default_url,
                               help="http path to the root of the zope server (default: %s)" % default_url)
        self.parser.add_option("--monitor", dest="monitor",
            default=DEFAULT_MONITOR,
            help="Name of monitor instance to use for heartbeat "
                " events. Default is %s." % DEFAULT_MONITOR)
        self.parser.add_option('--maintenance-window-cycletime',
            dest='maintenceWindowCycletime', default=60, type="int",
            help="How often to check to see if there are any maintenance windows to execute")

    def run(self):
        # Configure all actions with the command-line options
        options_dict = dict(vars(self.options))
        for name, action in getUtilitiesFor(IAction):
            action.configure(options_dict)

        task = ProcessSignalTask(NotificationDao(self.dmd))

        if self.options.daemon:
            self._callHomeCycler.start()
            self._maintenanceCycle.start()
            self._schedule.start()
        if self.options.daemon and self.options.workers > 1:
            self._workers.startWorkers()

        self._consumer = QueueConsumer(task, self.dmd)
        reactor.callWhenRunning(self._start)
        reactor.run()

    def _start(self):
        log.info('starting zenactiond consumer.')
        reactor.addSystemEventTrigger('before', 'shutdown', self._shutdown)
        self._consumer.run()


    @defer.inlineCallbacks
    def _shutdown(self, *ignored):
        log.info("Shutting down...")
        self._maintenanceCycle.stop()
        self._workers.shutdown()
        if self._consumer:
            yield self._consumer.shutdown()


if __name__ == '__main__':
    zad = ZenActionD()
    zad.run()
