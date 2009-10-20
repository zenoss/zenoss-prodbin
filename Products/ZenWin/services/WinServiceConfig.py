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

"Provides Wmi config to zenwin clients."

from Products.ZenCollector.services.config import CollectorConfigService

import logging
log = logging.getLogger('zen.ModelerService.WinServiceConfig')

class SmartService(object):
    "wraps a service and provides helper methods"
    
    def __init__(self, service):
        self._service = service
        
    def __getattr__(self, name):
        "delegate to the wrapped service"
        return getattr(self._service, name)
        
    @property
    def isMonitored(self):
        "is the service monitored"
        return self._service.getStatus() >= 0
        
    @property
    def name(self):
        "converts unicode service names"
        name = self._service.name()
        if type(name) == type(u''):
            name = name.encode(self._service.zCollectorDecoding)
        return name
        
    @property
    def severity(self):
        return self._service.getAqProperty('zFailSeverity')
        
def genServices(device):
    "generate services wrapped as SmartServices"
    for service in device.getMonitoredComponents(type='WinService'):
        yield SmartService(service)
        
class WinServiceConfig(CollectorConfigService):
    
    def __init__(self, dmd, instance):
        deviceProxyAttributes = ('zWmiMonitorIgnore',
                                 'zWinUser',
                                 'zWinPassword')
        CollectorConfigService.__init__(self, dmd, instance, deviceProxyAttributes)
        
    def _filterDevice(self, device):
        include = CollectorConfigService._filterDevice(self, device)
        
        if getattr(device, 'zWmiMonitorIgnore', False):
            self.log.debug("Device %s skipped because zWmiMonitorIgnore is True",
                           device.id)
            include = False
            
        return include
        
    def _createDeviceProxy(self, device):
        proxy = CollectorConfigService._createDeviceProxy(self, device)
        
        # for now, every device gets a single configCycleInterval based upon
        # the collector's winCycleInterval configuration which is typically
        # located at dmd.Monitors.Performance._getOb('localhost').
        # TODO: create a zProperty that allows for individual device schedules
        proxy.configCycleInterval = self._prefs.winCycleInterval
        
        proxy.services = {}
        for service in genServices(device):
            if service.isMonitored:
                proxy.services[service.name] = (service.getStatus(),
                                                service.severity)
                
        # don't bother adding this device proxy if there aren't any services
        # to monitor
        if not proxy.services:
            log.debug("Device %s skipped because there are no services",
                      proxy.id)
            return None
            
        return proxy
        
