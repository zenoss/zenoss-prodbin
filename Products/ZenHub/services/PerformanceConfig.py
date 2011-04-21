###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import Globals
from Products.ZenEvents.ZenEventClasses import Status_Snmp

from Products.ZenHub.HubService import HubService
from Products.ZenHub.PBDaemon import translateError

from Products.ZenModel.Device import Device
from Products.ZenModel.ZenPack import ZenPack
from Products.ZenModel.PerformanceConf import PerformanceConf
from Products.ZenHub.zodb import onUpdate, onDelete
from Acquisition import aq_parent

from twisted.internet import defer

from Procrastinator import Procrastinate
from ThresholdMixin import ThresholdMixin

ATTRIBUTES = (
    'id',
    'manageIp',
    'zMaxOIDPerRequest',
    'zSnmpMonitorIgnore',
    'zSnmpAuthPassword',
    'zSnmpAuthType',
    'zSnmpCommunity',
    'zSnmpPort',
    'zSnmpPrivPassword',
    'zSnmpPrivType',
    'zSnmpSecurityName',
    'zSnmpTimeout',
    'zSnmpTries',
    'zSnmpVer',
    )

from twisted.spread import pb
class SnmpConnInfo(pb.Copyable, pb.RemoteCopy):
    "A class to transfer the many SNMP values to clients"
    
    def __init__(self, device):
        "Store the properties from the device"
        for propertyName in ATTRIBUTES:
            setattr(self, propertyName, getattr(device, propertyName, None))
            self.id = device.id

    def __cmp__(self, other):
        for propertyName in ATTRIBUTES:
            c = cmp(getattr(self, propertyName), getattr(other, propertyName))
            if c != 0:
                return c
        return 0

    def summary(self):
        result = 'SNMP info for %s at %s:%s' % (
            self.id, self.manageIp, self.zSnmpPort)
        result += ' timeout: %s tries: %d' % (
            self.zSnmpTimeout, self.zSnmpTries)
        result += ' version: %s ' % (self.zSnmpVer)
        if '3' not in self.zSnmpVer:
            result += ' community: %s' % self.zSnmpCommunity
        else:
            result += ' securityName: %s' % self.zSnmpSecurityName
            result += ' authType: %s' % self.zSnmpAuthType
            result += ' privType: %s' % self.zSnmpPrivType
        return result

    def createSession(self, protocol=None, allowCache=False):
        "Create a session based on the properties"
        from pynetsnmp.twistedsnmp import AgentProxy
        cmdLineArgs=[]
        if '3' in self.zSnmpVer:
            if self.zSnmpPrivType:
                cmdLineArgs += ['-l', 'authPriv']
                cmdLineArgs += ['-x', self.zSnmpPrivType]
                cmdLineArgs += ['-X', self.zSnmpPrivPassword]
            elif self.zSnmpAuthType:
                cmdLineArgs += ['-l', 'authNoPriv']
            else:
                cmdLineArgs += ['-l', 'noAuthNoPriv']
            if self.zSnmpAuthType:
                cmdLineArgs += ['-a', self.zSnmpAuthType]
                cmdLineArgs += ['-A', self.zSnmpAuthPassword]
            cmdLineArgs += ['-u', self.zSnmpSecurityName]
        p = AgentProxy(ip=self.manageIp,
                       port=self.zSnmpPort,
                       timeout=self.zSnmpTimeout,
                       snmpVersion=self.zSnmpVer,
                       community=self.zSnmpCommunity,
                       cmdLineArgs=cmdLineArgs,
                       protocol=protocol,
                       allowCache=allowCache)
        p.snmpConnInfo = self
        return p

    def __repr__(self):
        return '<%s for %s>' % (self.__class__, self.id)
        
pb.setUnjellyableForClass(SnmpConnInfo, SnmpConnInfo)
        

class PerformanceConfig(HubService, ThresholdMixin):

    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)
        self.config = self.dmd.Monitors.Performance._getOb(self.instance)
        self.procrastinator = Procrastinate(self.pushConfig)
        self._collectorMap = {}


    @translateError
    def remote_propertyItems(self):
        return self.config.propertyItems()


    def remote_getDefaultRRDCreateCommand(self, *args, **kwargs):
        return self.config.getDefaultRRDCreateCommand(*args, **kwargs)


    def notifyAll(self, device):
        self.procrastinator.doLater(device)


    def pushConfig(self, device):
        deferreds = []
        cfg = None

        cur_collector = device.perfServer.getRelatedId()
        prev_collector = self._collectorMap.get(device.id, None)
        self._collectorMap[device.id] = cur_collector

        # Always push config to currently assigned collector.
        if cur_collector == self.instance:
            cfg = self.getDeviceConfig(device)

        # Push a deleteDevice call if the device was previously assigned to
        # this collector.
        elif prev_collector and prev_collector == self.instance:
            cfg = None

        # Don't do anything if this collector is not, and has not been involved
        # with the device
        else:
            return defer.DeferredList(deferreds)

        for listener in self.listeners:
            if cfg is None:
                deferreds.append(listener.callRemote('deleteDevice', device.id))
            else:
                deferreds.append(self.sendDeviceConfig(listener, cfg))
        return defer.DeferredList(deferreds)


    def getDeviceConfig(self, device):
        "How to get the config for a device"
        return None


    def sendDeviceConfig(self, listener, config):
        "How to send the config to a device, probably via callRemote"
        pass


    @onUpdate(PerformanceConf)
    def perfConfUpdated(self, object, event):
        if object.id == self.instance:
            for listener in self.listeners:
                listener.callRemote('setPropertyItems', object.propertyItems())

    @onUpdate(ZenPack)
    def zenPackUpdated(self, object, event):
        for listener in self.listeners:
            try:
                listener.callRemote('updateThresholdClasses',
                                    self.remote_getThresholdClasses())
            except Exception, ex:
                self.log.warning("Error notifying a listener of new classes")

    @onUpdate(Device)
    def deviceUpdated(self, object, event):
        self.notifyAll(object)

    @onUpdate(None) # Matches all
    def notifyAffectedDevices(self, object, event):
        if isinstance(object, Device):
            return

        # something else... mark the devices as out-of-date
        from Products.ZenModel.DeviceClass import DeviceClass

        while object:
            # walk up until you hit an organizer or a device
            if isinstance(object, DeviceClass):
                for device in object.getSubDevices():
                    self.notifyAll(device)
                break

            if isinstance(object, Device):
                self.notifyAll(object)
                break

            object = aq_parent(object)

    @onDelete(Device)
    def deviceDeleted(self, object, event):
        devid = object.id
        for listener in self.listeners:
            listener.callRemote('deleteDevice', devid)
