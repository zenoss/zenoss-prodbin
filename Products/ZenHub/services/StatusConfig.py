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

from Procrastinator import Procrastinate

from twisted.internet import defer
from sets import Set

from twisted.spread import pb
class ServiceConfig(pb.Copyable, pb.RemoteCopy):
    
    def __init__(self, svc):
        self.device = svc.hostname()
        self.component = svc.name()
        self.ip = svc.getManageIp()
        self.port = svc.getPort()
        self.sendString = svc.getSendString()
        self.expectRegex = svc.getExpectRegex()
        self.timeout = svc.zStatusConnectTimeout
        self.failSeverity = svc.getFailSeverity()
        self.key = svc.key()
pb.setUnjellyableForClass(ServiceConfig, ServiceConfig)

class StatusConfig(HubService):

    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)
        self.config = self.dmd.Monitors.Performance._getOb(self.instance)
        self.procrastinator = Procrastinate(self.notify)

    def remote_propertyItems(self):
        return self.config.propertyItems()

    def remote_serviceStatus(self):
        zem = self.dmd.ZenEventManager
        status = zem.getAllComponentStatus(Status_IpService)
        devices = Set([d.id for d in self.config.devices()])
        return [x for x in status.items() if x[0][0] in devices]

    def remote_services(self, unused):
        result = []
        for dev in self.config.devices():
            dev = dev.primaryAq()
            if not dev.monitorDevice(): continue
            for svc in dev.getMonitoredComponents(collector='zenstatus'):
                if svc.getProtocol() != "tcp": continue
                result.append(ServiceConfig(svc))
        return result

    def remote_getDefaultRRDCreateCommand(self):
        return self.config.getDefaultRRDCreateCommand()

        
    def update(self, object):
        if not self.listeners: return

        # the PerformanceConf changed
        from Products.ZenModel.PerformanceConf import PerformanceConf
        if isinstance(object, PerformanceConf):
            for listener in self.listeners:
                listener.callRemote('setPropertyItems', object.propertyItems())
        self.procrastinator.doLater()

    def notify(self, unused):
        lst = []
        for listener in self.listeners:
            lst.append(listener.callRemote('notifyConfigChanged'))
        return defer.DeferredList(lst)

    def deleted(self, obj):
        for listener in self.listeners:
            if isinstance(obj, Device):
                listener.callRemote('deleteDevice', obj.id)
