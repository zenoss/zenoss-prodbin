##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from .jobs import Job
from Products.DataCollector.ApplyDataMap import ApplyDataMap
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

class DeviceApplyDataMapsJob(Job):
    """
    Takes a device and calls applyDataMap.
    """

    @classmethod
    def getJobType(cls):
        return "Device ApplyDataMap"

    @classmethod
    def getJobDescription(cls, **kwargs):
        return "ApplyDataMap"

    def _run(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.adm = ApplyDataMap()
        maps = self.kwargs['maps']
        uid = self.kwargs['uid']
        log.info("About to call applyDataMap for uid: %s " % uid)
        device = self.dmd.unrestrictedTraverse(uid)
        for map in maps:
            self.adm._applyDataMap(device, map)
