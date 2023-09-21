##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, 2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging
import os
import signal

from optparse import SUPPRESS_HELP
from time import sleep

from zope.component import getAdapter, getGlobalSiteManager

from Products.ZenUtils.CmdBase import CmdBase
from Products.ZenUtils.ZCmdBase import ZCmdBase

from .modelchange.configstore import DeviceConfigStore, MonitorDeviceMapStore
from .modelchange.interfaces import InvalidationPoller
from .modelchange.manager import InvalidationManager
from .modelchange.services import getConfigServices

IDLE = "None/None"


def getLogger(obj):
    """Return a logger based on the name of the given class."""
    cls = type(obj)
    name = "zen.zenmodelchange.%s" % (cls.__name__)
    return logging.getLogger(name)


class ZenModelChange(ZCmdBase):
    """Monitor model invalidations and (re)create device configurations."""

    mname = name = "zenmodelchange"

    def __init__(self):
        """Initialize a ZenModelChange instance."""
        ZCmdBase.__init__(self)

        self.zem = self.dmd.ZenEventManager

        self.__config_module_names = None
        self.__monitorStore = None
        self.__configStores = None

    def runInvalidationMonitor(self):
        self._setup()

        # Monitor invalidations
        # poller = getAdapter(self.storage, InvalidationPoller)
        # im = InvalidationManager(self.dmd, poller)
        # while True:
        #     updates = im.poll()
        #     if updates:
        #         pass
        #     sleep(1)

    def runConfigGenerator(self):
        """
        """

    def _setup(self):
        self.log.debug("establishing SIGUSR1 signal handler")
        signal.signal(signal.SIGUSR1, self.sighandler_USR1)

        self.__config_module_names = tuple(
            cls.__module__ for cls in getConfigServices()
        )
        self.__monitorStore = MonitorDeviceMapStore.make()
        self.__configStores = {
            name: DeviceConfigStore.make(name)
            for name in self.__config_module_names
        }

        # Initial configuration load
        # 1. Get the list of monitors for current hub.
        # 2.
        # monitors = getAdapter(self.dmd, IMonitor, "monitors")

    def _reportStats(self):
        """Write zenmodelchange's current statistics to the log."""
        self.log.info("no statistics")

    def buildOptions(self):
        """Add optparse options to the options parser."""
        ZCmdBase.buildOptions(self)
        self.parser.add_option(
            "--workerid", type="int", default=0, help=SUPPRESS_HELP
        )
        self.parser.add_option(
            "--workers", type="int", default=1, help=SUPPRESS_HELP
        )


def main():
    zmc = ZenModelChange()
    if zmc.options.workerid == 0:
        zmc.runInvalidationMonitor()
    else:
        zmc.runConfigGenerator()
