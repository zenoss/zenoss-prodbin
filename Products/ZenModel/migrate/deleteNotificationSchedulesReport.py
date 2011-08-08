###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import Migrate

import Globals

import logging
log = logging.getLogger("zen.migrate")


class DeleteNotificationSchedulesReport(Migrate.Step):
    version = Migrate.Version(4, 0, 0)

    def cutover(self, dmd):
        USER_REPORTS_CATEGORY = 'User Reports'
        NOTIFICATION_SCHEDULES_REPORT = 'Notification Schedules'

        userReports = getattr(dmd.Reports, USER_REPORTS_CATEGORY, {})
        if NOTIFICATION_SCHEDULES_REPORT in userReports:
            del userReports[NOTIFICATION_SCHEDULES_REPORT]


DeleteNotificationSchedulesReport()
