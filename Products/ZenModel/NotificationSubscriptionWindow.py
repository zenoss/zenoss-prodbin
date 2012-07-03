###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging

log = logging.getLogger("zen.notificationwindows")

import time
from Products.ZenRelations.RelSchema import *
from Products.ZenModel.MaintenanceWindow import MaintenanceWindow

class NotificationSubscriptionWindow(MaintenanceWindow):

    notificationSubscription = None

    backCrumb = "triggers"

    _relations = MaintenanceWindow._relations + (
        ("notificationSubscription",
        ToOne(
            ToManyCont,
            "Products.ZenModel.NotificationSubscription",
            "windows"
        )),
    )

    _properties = tuple(list(MaintenanceWindow._properties) + [
        {'id':'enabled', 'type':'boolean', 'mode':'w'}
    ])

    def target(self):
        return self.notificationSubscription()

    def begin(self, now=None):
        if self.started is not None:
            log.debug('Notification Subscription Window is trying to begin after'
                ' it is already started: Start: %s, Duration: %s' % (self.started, self.duration))

        self.target().enabled = True
        if not now:
            now = time.time()
        self.started = now

    def end(self):
        self.started = None
        self.target().enabled = False
