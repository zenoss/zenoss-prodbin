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

from PerformanceConfig import PerformanceConfig
from ZODB.POSException import POSError
from Products.ZenRRD.zencommand import Cmd, DeviceConfig, DataPointConfig
from Products.ZenRRD.CommandParser import getParser
from Products.ZenHub.PBDaemon import translateError


def getComponentCommands(comp, commandCache, commandSet):
    """Return list of command definitions.
    """
    perfServer = comp.device().getPerformanceServer()
    for templ in comp.getRRDTemplates():
        basepath = comp.rrdPath()
        for ds in templ.getRRDDataSources('COMMAND'):
            if not ds.enabled: continue
            parserName = getattr(ds, "parser", "Auto")
            parser = getParser(parserName)
            points = []
            for dp in ds.getRRDDataPoints():
                dpc = DataPointConfig()
                dpc.id = dp.id
                dpc.component = comp.id
                dpc.rrdPath = "/".join((basepath, dp.name()))
                dpc.rrdType = dp.rrdtype
                dpc.rrdCreateCommand = dp.getRRDCreateCommand(perfServer)
                dpc.rrdMin = dp.rrdmin
                dpc.rrdMax = dp.rrdmax
                dpc.data = parser.dataForParser(comp, dp)
                points.append(dpc)
            cmd = Cmd()
            cmd.useSsh = getattr(ds, 'usessh', False)
            cmd.cycleTime = ds.cycletime
            cmd.component = ds.getComponent(comp)
            cmd.eventClass = ds.eventClass
            cmd.eventKey = ds.eventKey or ds.id
            cmd.severity = ds.severity
            cmd.parser = parserName
            cmd.command = ds.getCommand(comp)
            cmd = commandCache.setdefault(cmd.commandKey(), cmd)
            cmd.points.extend(points)
            commandSet.add(cmd)
    return comp.getThresholdInstances('COMMAND')


def getDeviceCommands(dev):
    if not dev.monitorDevice():
        return None
    cache = {}
    cmds = set()
    threshs = getComponentCommands(dev, cache, cmds)
    for o in dev.getMonitoredComponents(collector="zencommand"):
        threshs.extend(getComponentCommands(o, cache, cmds))
    if cmds:
        d = DeviceConfig()
        d.lastChange = dev.getLastChange()
        d.device = dev.id
        d.ipAddress = dev.getManageIp()
        d.port = dev.zCommandPort
        d.username = dev.zCommandUsername
        d.password = dev.zCommandPassword
        d.loginTimeout = dev.zCommandLoginTimeout
        d.commandTimeout = dev.zCommandCommandTimeout
        d.keyPath = dev.zKeyPath
        d.maxOids = dev.zMaxOIDPerRequest
        d.commands = list(cmds)
        d.thresholds = threshs
        return d
    return None


class CommandConfig(PerformanceConfig):

    @translateError
    def remote_getDataSourceCommands(self, devices = None):
        return self.getDataSourceCommands(devices)


    def getDeviceConfig(self, device):
        return getDeviceCommands(device)


    def sendDeviceConfig(self, listener, config):
        return listener.callRemote('updateConfig', config)


    def getDataSourceCommands(self, devices = None):
        '''Get the command configuration for all devices.
        '''
        result = []
        for dev in self.config.devices():
            if devices and dev.id not in devices: continue
            dev = dev.primaryAq()
            try:
                cmdinfo = getDeviceCommands(dev)
                if not cmdinfo: continue
                result.append(cmdinfo)
            except POSError: raise
            except:
                self.log.exception("device %s", dev.id)
        return result

    def update(self, object):
        from Products.ZenModel.RRDDataSource import RRDDataSource
        if isinstance(object, RRDDataSource):
            if object.sourcetype != 'COMMAND':
                return

        PerformanceConfig.update(self, object)
        
