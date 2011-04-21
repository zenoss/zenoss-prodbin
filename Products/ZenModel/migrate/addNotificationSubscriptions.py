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

import Migrate
from Products.ZenModel.NotificationSubscription import NotificationSubscriptionManager, \
    manage_addNotificationSubscriptionManager
from Products.Zuul.utils import safe_hasattr as hasattr

class NotificationSubscriptions(Migrate.Step):
    version = Migrate.Version(3,1,70)
    
    def cutover(self, dmd):
        if not hasattr(dmd, NotificationSubscriptionManager.root):
            manage_addNotificationSubscriptionManager(dmd)

notificationSubscriptions = NotificationSubscriptions()