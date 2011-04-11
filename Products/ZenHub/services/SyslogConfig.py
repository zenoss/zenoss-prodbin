###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = '''SyslogConfig

Provides configuration for syslog message to Zenoss event conversions.
'''

import logging
log = logging.getLogger('zen.HubService.SyslogConfig')

import Globals

from Products.ZenCollector.services.config import CollectorConfigService
from Products.ZenHub.zodb import onUpdate, onDelete


class FakeDevice(object):
    id = 'Syslog payload'


class SyslogConfig(CollectorConfigService):
    def _filterDevices(self, deviceList):
        return [ FakeDevice() ]

    def _createDeviceProxy(self, device):
        proxy = CollectorConfigService._createDeviceProxy(self, device)
        proxy.configCycleInterval = 3600
        proxy.name = "Syslog Configuration"
        proxy.device = device.id

        proxy.defaultPriority = self.zem.defaultPriority
        return proxy


if __name__ == '__main__':
    from Products.ZenHub.ServiceTester import ServiceTester
    tester = ServiceTester(SyslogConfig)
    def printer(config):
        print "Default syslog priority = ", config.defaultPriority
    tester.printDeviceProxy = printer
    tester.showDeviceInfo()

