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

__doc__='''WmiService

Provides Wmi config to zenwin clients.
'''

from Products.ZenHub.services.ModelerService import ModelerService
from Products.ZenModel.Device import Device
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.WinService import WinService
from Products.ZenModel.ServiceClass import ServiceClass
from Products.ZenModel.ServiceOrganizer import ServiceOrganizer

from Products.ZenHub.services.Procrastinator import Procrastinate
from Products.ZenHub.services.ThresholdMixin import ThresholdMixin

import logging
log = logging.getLogger('zen.ModelerService.WmiConfig')

class WmiConfig(ModelerService, ThresholdMixin):


    def __init__(self, dmd, instance):
        ModelerService.__init__(self, dmd, instance)
        self.config = self.dmd.Monitors.Performance._getOb(self.instance)
        self.procrastinator = Procrastinate(self.push)


    def createDeviceProxy(self, dev):
        result = ModelerService.createDeviceProxy(self, dev)
        for prop in (
            'zWmiMonitorIgnore', 
            'zWinUser',
            'zWinPassword',
            'zWinEventlogMinSeverity'):
            if hasattr(dev, prop):
                setattr(result, prop, getattr(dev, prop))
        return result


    def remote_getConfig(self):
        return self.config.propertyItems()


    def update(self, object):
        objects = []
        if isinstance(object, DeviceClass):
            objects = object.getSubDevices()
        elif isinstance(object, WinService):
            objects = [object.device()]
        elif isinstance(object, ServiceClass):
            objects = [ i.device() for i in object.instances() \
                if isinstance(i, WinService) ]
        elif isinstance(object, ServiceOrganizer):
            
            #only need to find one device with a WinService to determine if a 
            #config change notification needs to be sent. This is because 
            #config changes are not sent for each device, if any device has 
            #changed the notifyConfigChanged method is called on the collector
            #which tells the collector to re-read the entire configuration
            def scanHeirarchyForDevice( organizer ):
                
                #find device with a winserivce in an organizers service classes
                def getWinServiceDevice( organizer ):
                    for sc in organizer.serviceclasses():
                        for inst in sc.instances():
                            if isinstance(inst,WinService):
                                return inst.device()
                                
                    return None
                
                organizers = [organizer]
                #iterate through all the organizers and children 'till a device
                #is found
                while organizers:
                    for org in organizers:
                        device = getWinServiceDevice(org)
                        if device:
                            return device
                    
                    oldOrgs = organizers
                    organizers = []
                    for org in oldOrgs:
                        organizers.extend(org.children())
                
                return None
                
            device = scanHeirarchyForDevice( object )
            
            if device:
                objects = [device]
            
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


    def _monitoredDevices(self, names):
        """
        A generator method that provides a list of devices that are set to be
        monitored via WMI.
        """
        deviceMap = {}

        for name in names:
            # try and load the device from the provided list of names, but
            # exclude the device if a) we can't find it! or b) we've already
            # found it and created a proxy. The latter is a guard against
            # two different proxies for the same device being provided which
            # will cause great grief with the native code DCOM implementation
            # we use.
            device = self.dmd.Devices.findDeviceByIdExact(name)
            if not device:
                continue
            elif deviceMap.has_key(device.id):
                continue

            device = device.primaryAq()

            # make sure the device itself is being monitored
            if not device.monitorDevice():
                log.debug("Device %s skipped because monitoring is disabled",
                          device.id)
                continue

            # now make sure the  WMI specific monitoring flag is enabled
            if getattr(device, 'zWmiMonitorIgnore', False):
                log.debug("Device %s skipped because zWmiMonitorIgnore is set",
                          device.id)
                continue

            # return the monitored device to the generator caller
            yield device


    def remote_getDeviceConfigForEventlog(self, names):
        """Return a list of (devname, user, password)
        """
        deviceProxies = []

        for device in self._monitoredDevices(names):
            if not getattr(device, 'zWinEventlog', True):
                log.debug("Device %s skipped because zWinEventlog is cleared", 
                          device.id)
                continue

            proxy = self.createDeviceProxy(device)
            proxy.id = device.getId()

            deviceProxies.append(proxy)
            log.debug("Device %s added to proxy list", proxy.id)

        return deviceProxies


    def remote_getDeviceConfigAndWinServices(self, names):
        """Return a list of (devname, user, passwd, {'EvtSys':0,'Exchange':0}) 
        """
        deviceProxies = []
        for device in self._monitoredDevices(names):

            proxy = self.createDeviceProxy(device)
            proxy.id = device.getId()

            proxy.services = {}
            for s in device.getMonitoredComponents(type='WinService'):
                name = s.name()
                if type(name) == type(u''):
                    name = name.encode(s.zCollectorDecoding)
                proxy.services[name] = (s.getStatus(), 
                                        s.getAqProperty('zFailSeverity'))

            # don't bother adding this device proxy if there aren't any services
            # to monitor
            if not proxy.services:
                log.debug("Device %s skipped because there are no services",
                          proxy.id)
                continue

            deviceProxies.append(proxy)
            log.debug("Device %s added to proxy list", proxy.id)

        return deviceProxies
