###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007-2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__='''EventLogConfig

Provides configuration to zeneventlog clients.
'''

from Products.ZenCollector.services.config import CollectorConfigService

import logging
log = logging.getLogger('zen.ModelerService.EventLogConfig')

class EventLogConfig(CollectorConfigService):
    def __init__(self, dmd, instance):
        deviceProxyAttributes = ('zWmiMonitorIgnore',
                                 'zWinUser',
                                 'zWinPassword',
                                 'zWinEventlogMinSeverity')
        CollectorConfigService.__init__(self, dmd, instance, deviceProxyAttributes)

    def _filterDevice(self, device):
        include = CollectorConfigService._filterDevice(self, device)

        if getattr(device, 'zWmiMonitorIgnore', False):
            self.log.debug("Device %s skipped because zWmiMonitorIgnore is True",
                           device.id)
            include = False

        elif not getattr(device, 'zWinEventlog', True):
            log.debug("Device %s skipped because zWinEventlog is False",
                      device.id)
            include = False

        return include

    def _createDeviceProxy(self, device):
        proxy = CollectorConfigService._createDeviceProxy(self, device)

        # for now, every device gets a single configCycleInterval based upon
        # the collector's eventlogCycleInterval configuration.
        # TODO: create a zProperty that allows for individual device schedules
        proxy.configCycleInterval = self._prefs.eventlogCycleInterval

        return proxy
