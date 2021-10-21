#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
#
# Copyright (C) Zenoss, Inc. 2007, 2010, 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
#


__doc__ = """zenping

Determines the availability of a IP addresses using ping (ICMP).

"""
import sys
import os.path
import logging
log = logging.getLogger("zen.zenping")

import Globals
import zope.interface
import zope.component

from Products import ZenStatus
from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector import tasks
from Products.ZenUtils import IpUtil
from Products.ZenUtils.FileCache import FileCache

# perform some imports to allow twisted's PB to serialize these objects
from Products.ZenUtils.Utils import unused, zenPath
from Products.ZenCollector.services.config import DeviceProxy
from Products.ZenHub.services.PingPerformanceConfig import PingPerformanceConfig
unused(DeviceProxy)
unused(PingPerformanceConfig)
unused(Globals)

# define some constants strings
COLLECTOR_NAME = "zenping"
CONFIG_SERVICE = 'Products.ZenHub.services.PingPerformanceConfig'


class PingDaemon(CollectorDaemon):

    def runPostConfigTasks(self, result=None):
        CollectorDaemon.runPostConfigTasks(self, result=result)
        self.preferences.runPostConfigTasks()


class PerIpAddressTaskSplitter(tasks.SubConfigurationTaskSplitter):
    subconfigName = 'monitoredIps'

    def makeConfigKey(self, config, subconfig):
        return config.id, subconfig.cycleTime, IpUtil.ipunwrap(subconfig.ip)


def getConfigOption(filename, option, default):
    """
    Look for config option in file.
    """
    if not os.path.exists(filename):
        return default
    with open(filename, 'r') as f:
        lines = [line.strip() for line in f.readlines() if not line.startswith('#') and line]
        for line in reversed(lines):
            parts = line.split()
            if len(parts):
                if parts[0] == option:
                    if len(parts) < 2:
                        return True
                    return parts[1]
    return default


def getCmdOption(option, default):
    """
    Introspect the command line args to find --option because
    buildOptions doesn't get called until later.
    """
    try:
        optionStr = "--%s" % option
        optionStrEq = "--%s=" % option
        for i, arg in enumerate(sys.argv):
            if arg == optionStr:
                return sys.argv[i + 1]
            elif arg.startswith(optionStrEq):
                return arg.split('=', 1)[1]
    except IndexError:
        pass
    return default


def getPingBackend():
    """
    Introspect the command line args to find --ping-backend because
    buildOptions doesn't get called until later.
    """

    monitor = getCmdOption('monitor', 'localhost')

    configFiles = ['global.conf']
    if monitor == 'localhost':
        configFiles.append("zenping.conf")
    else:
        configFiles.append("%s_zenping.conf" % monitor)

    backend = 'nmap'
    for configFile in configFiles:
        backend = getConfigOption(zenPath('etc', configFile), 'ping-backend', backend)
    return backend


if __name__ == '__main__':

    # load zcml for the product
    import Products.ZenossStartup
    from Zope2.App import zcml
    zcml.load_site()
    pingBackend = getPingBackend()

    myPreferences = zope.component.getUtility(
        ZenStatus.interfaces.IPingCollectionPreferences, pingBackend)
    myTaskFactory = zope.component.getUtility(ZenStatus.interfaces.IPingTaskFactory, pingBackend)
    myTaskSplitter = PerIpAddressTaskSplitter(myTaskFactory)

    myDaemon = PingDaemon(
        myPreferences,
        myTaskSplitter,
        stoppingCallback=myPreferences.preShutdown,
    )

    # add trace cache to preferences, so tasks can find it
    traceCachePath = zenPath('var', 'zenping', myDaemon.options.monitor)
    myPreferences.options.traceCache = FileCache(traceCachePath)

    myDaemon.run()
