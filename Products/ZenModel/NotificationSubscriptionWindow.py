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
log = logging.getLogger("zen.notificationwindows")

from Products.ZenRelations.RelSchema import *
from Products.ZenModel.MaintenanceWindow import MaintenanceWindow

class NotificationSubscriptionWindow(MaintenanceWindow):
    _relations = (
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