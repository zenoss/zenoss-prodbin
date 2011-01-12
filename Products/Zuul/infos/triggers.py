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

from datetime import datetime
from time import time
from zope.interface import implements
from Products.Zuul.infos import InfoBase, ProxyProperty
from Products.ZenModel.MaintenanceWindow import MaintenanceWindow
from zope.schema.vocabulary import SimpleVocabulary
from Products.ZenModel.NotificationSubscription import NotificationSubscription
from Products.Zuul.interfaces import INotificationWindowInfo, INotificationSubscriptionInfo

class NotificationSubscriptionInfo(InfoBase):
    implements(INotificationSubscriptionInfo)

    @property
    def newId(self):
        return self._object.id

    enabled = ProxyProperty('enabled')
    send_clear = ProxyProperty('send_clear')
    send_initial_occurrence = ProxyProperty('send_initial_occurrence')

    delay_seconds = ProxyProperty('delay_seconds')
    repeat_seconds = ProxyProperty('repeat_seconds')
    action_timeout = ProxyProperty('action_timeout')

    action = ProxyProperty('action')
    body_content_type = ProxyProperty('body_content_type')

    subject_format =ProxyProperty('subject_format')
    body_format = ProxyProperty('body_format')
    clear_subject_format =ProxyProperty('clear_subject_format')
    clear_body_format = ProxyProperty('clear_body_format')

    recipients = ProxyProperty('recipients')
    #explicit_recipients = ProxyProperty('explicit_recipients')

    def _getSubscriptions(self):
        if self._object.subscriptions:
            return self._object.subscriptions[0]
        else:
            return ''
    def _setSubscriptions(self, value):
        self._object.subscriptions = [value]

    subscriptions = property(_getSubscriptions, _setSubscriptions)


class NotificationWindowInfo(InfoBase):
    implements(INotificationWindowInfo)

    @property
    def newId(self):
        return self._object.id

    def _getStart(self):
        # is a unix timestamp convert to string
        start = time()
        try:
            start = float(self._object.start)
        except (ValueError, TypeError):
            pass
        dt = datetime.utcfromtimestamp(start)
        # we want the format in mm/dd/yyyy
        return "%.2d/%.2d/%d" % (dt.month, dt.day, dt.year)

    def _setStart(self, value):
        # convert string to unix time stamp
        # expecting the time to always be in the following format
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        self._object.start = dt.strftime('%s')

    def _getStartTime(self):
        starttime = time()
        try:
            starttime = float(self._object.start)
        except (ValueError, TypeError):
            pass
        dt = datetime.fromtimestamp(starttime)
        return '%.2d:%.2d' % (dt.hour, dt.minute)

    def _setStartTime(self, value):
        pass

    start = property(_getStart, _setStart)
    starttime = property(_getStartTime, _setStartTime)
    enabled = ProxyProperty('enabled')
    repeat = ProxyProperty('repeat')
    duration = ProxyProperty('duration')
