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
#! /usr/bin/env python 

from Products.ZenHub.HubService import HubService

from Products.ZenEvents.ZenEventClasses import Status_IpService
from Products.ZenModel.Device import Device
from Acquisition import aq_parent, aq_base

from twisted.internet import reactor, defer
from sets import Set

from twisted.spread import pb
class ServiceConfig(pb.Copyable, pb.RemoteCopy):
    
    def __init__(self, svc):
        self.device = svc.hostname()
        self.component = svc.name()
        self.ip = svc.getManageIp()
        self.port = svc.getPort()
        self.sendString = svc.getSendString()
        self.expectString = svc.getExpectRegex()
        self.timeout = svc.zStatusConnectTimeout
        self.failSeverity = svc.getFailSeverity()
        self.key = svc.key()
pb.setUnjellyableForClass(ServiceConfig, ServiceConfig)

class StatusConfig(HubService):

    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)
        self.config = self.dmd.Monitors.StatusMonitors._getOb(self.instance)

    def remote_propertyItems(self):
        return self.config.propertyItems()

    def remote_serviceStatus(self):
        zem = self.dmd.ZenEventManager
        status = zem.getAllComponentStatus(Status_IpService)
        devices = Set([d.id for d in self.config.devices()])
        return [x for x in status.items() if x[0][0] in devices]

    def remote_services(self, configpath):
        smc = self.dmd.getObjByPath(configpath.lstrip('/'))
        result = []
        for svc in smc.getSubComponents("IpService"):
            dev = svc.device()
            if not dev.monitorDevice(): continue
            if svc.getProtocol() != "tcp": continue
            result.append(ServiceConfig(svc))
        return result
        
    def update(self, object):
        if not self.listeners: return

        # the PerformanceConf changed
        from Products.ZenModel.PerformanceConf import PerformanceConf
        if isinstance(object, PerformanceConf):
            for listener in self.listeners:
                listener.callRemote('setPropertyItems', object.propertyItems())
                devices = [
                    (d.id, float(d.getLastChange())) for d in object.devices()
                     ]
                # listener.callRemote('updateDeviceList', devices)

        for listener in self.listeners:
            listener.callRemote('notifyConfigChanged')

    def deleted(self, obj):
        for listener in self.listeners:
            if isinstance(obj, Device):
                listener.callRemote('deleteDevice', obj.id)
