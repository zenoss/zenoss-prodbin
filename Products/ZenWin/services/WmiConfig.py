###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__='''WmiService

Provides Wmi config to zenwin clients.
'''

from Products.ZenHub.services.ModelerService import ModelerService
from Products.ZenModel.Device import Device
from Products.ZenModel.DeviceClass import DeviceClass

from Products.ZenHub.services.Procrastinator import Procrastinate
from Products.ZenHub.services.ThresholdMixin import ThresholdMixin

class WmiConfig(ModelerService, ThresholdMixin):

    def __init__(self, dmd, instance):
        ModelerService.__init__(self, dmd, instance)
        self.config = self.dmd.Monitors.Performance._getOb(self.instance)
        self.procrastinator = Procrastinate(self.push)


    def remote_getConfig(self):
        return self.config.propertyItems()


    def update(self, object):
        if isinstance(object, DeviceClass):
            objects = object.getSubDevices()
        else:
            objects = [object]
        for object in objects:
            if not isinstance(object, Device):
                continue
            self.procrastinator.doLater(object)

    def push(self, object):
        if (not object.monitorDevice() or
            getattr(object, 'zWmiMonitorIgnore', False)):
            self.deleted(object)
        else:
            for listener in self.listeners:
                listener.callRemote('notifyConfigChanged')
            self.procrastinator.clear()

    def deleted(self, obj):
        for listener in self.listeners:
            if isinstance(obj, Device):
                listener.callRemote('deleteDevice', obj.id)


    def remote_getDeviceConfigAndWinServices(self, names):
        """Return a list of (devname, user, passwd, {'EvtSys':0,'Exchange':0}) 
        """
        result = []
        for name in names:
            device = self.dmd.Devices.findDevice(name)
            if not device:
                continue
            device = device.primaryAq()
            if (device.productionState <=
                getattr(device, 'zProdStateThreshold', 0)):
                continue
            if not device.monitorDevice(): continue
            if getattr(device, 'zWmiMonitorIgnore', False): continue
            
            proxy = self.createDeviceProxy(device)
            proxy.id = device.getId()
            proxy.services = {}
            for s in device.getMonitoredComponents(type='WinService'):
                name = s.name()
                if type(name) == type(u''):
                    name = name.encode(s.zCollectorDecoding)
                proxy.services[name] = (s.getStatus(), 
                                    s.getAqProperty('zFailSeverity'))
            if not proxy.services and not device.zWinEventlog: continue
            result.append(proxy)
        return result

