##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import threading

from .job import Job


class DeviceListJob(Job):
    """Return the names of Server/Linux devices."""

    name = "Products.Jobber.DeviceListJob"

    @classmethod
    def getJobDescription(cls, *args, **kwargs):
        return "some description"

    def _run(self, *args, **kw):
        deviceNames = [
            device.id for device in self.dmd.Devices.Server.Linux.devices()
        ]
        # attrs = ", ".join(dir(self))
        self.log.info("device names: %s", deviceNames)
        return deviceNames


class PausingJob(Job):
    """Waits for some interval of time before finishing successfully."""

    name = "Products.Jobber.PausingJob"

    @classmethod
    def getJobDescription(cls, *args, **kw):
        return "Runs for %s seconds" % args[0]

    def _run(self, seconds, *args, **kw):
        self.log.info("Sleeping for %s seconds", seconds)
        threading.Event().wait(seconds)


class DelayedFailure(Job):
    """Waits for some interval of time before failing."""

    name = "Products.Jobber.DelayedFailure"

    @classmethod
    def getJobDescription(cls, *args, **kw):
        return "Runs for %s seconds before failing" % args[0]

    def _run(self, seconds, *args, **kw):
        self.log.info("Sleeping for %s seconds", seconds)
        threading.Event().wait(seconds)
        raise ValueError("ka-boom!")
