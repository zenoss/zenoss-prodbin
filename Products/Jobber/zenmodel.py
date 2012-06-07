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
from .jobs import Job
import logging
log = logging.getLogger("zen.jobs.zenmodel")

class DeviceSetLocalRolesJob(Job):
    """
    Takes a device organizer and calls setAdminLocalRoles on each device.
    When someone updates a role on an organizer this is necessary to make sure that
    that user has permission on each of the devices in that organizer.
    """
    @classmethod
    def getJobType(cls):
        return "Device Set Local Roles"

    @classmethod
    def getJobDescription(cls, **kwargs):
        return "Setting Administrative roles"

    def _run(self, organizerUid, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        log.info("About to set local roles for uid: %s " % organizerUid)
        organizer = self.dmd.unrestrictedTraverse(organizerUid)
        organizer._setDeviceLocalRoles()
