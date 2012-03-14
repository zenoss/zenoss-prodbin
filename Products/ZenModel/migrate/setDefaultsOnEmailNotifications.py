###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """Set the default values for E-mail notifications"""

import logging
import Globals
from Products.ZenUtils.Utils import unused
from Products.ZenModel.migrate import Migrate

unused(Globals)

log = logging.getLogger('zen.migrate')

class setDefaultsOnEmailNotifications(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        log.info("Setting default values for E-mail notifications.")
        for notif in dmd.NotificationSubscriptions.objectValues():
            if notif.action == "email" and "host" not in notif.content:
                notif._p_changed = True
                notif.content["host"] = dmd.smtpHost
                notif.content["port"] = dmd.smtpPort
                notif.content["user"] = dmd.smtpUser
                notif.content["password"] = dmd.smtpPass
                notif.content["useTls"] = dmd.smtpUseTLS
                notif.content["email_from"] = dmd.getEmailFrom()

setDefaultsOnEmailNotifications()
