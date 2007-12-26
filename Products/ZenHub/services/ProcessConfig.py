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

from Products.ZenRRD.zenprocess import Device, Process

def getOSProcessConf(dev):
    """
    Returns process monitoring configuration
        
    @rtype: tuple (lastChangeTimeInSecs, (devname, (ip, port), 
    (community, version, timeout, tries), zMaxOIDPerRequest),
    list of configs, list of thresholds)
    """
    if not dev.snmpMonitorDevice():
        return None
    procs = dev.getMonitoredComponents(collector='zenprocess')
    if not procs:
        return None
    d = Device()
    d.name = dev.id
    d.lastChange = dev.getLastChange()
    d.thresholds = [t for p in procs for t in p.getThresholdInstances('SNMP')]
    d.snmpConnInfo = dev.getSnmpConnInfo()
    for p in procs:
        proc = Process()
        proc.name = p.id
        proc.originalName = p.name()
        proc.ignoreParameters = (
            getattr(p.osProcessClass(), 'ignoreParameters', False))
        proc.restart = p.alertOnRestart()
        proc.severity = p.getFailSeverity()
        d.processes[p.id] = proc
    return d


class ProcessConfig(PerformanceConfig):

    def getProcessStatus(self, device=None):
        "Get the known process status from the Event Manager"
        from Products.ZenEvents.ZenEventClasses import Status_OSProcess
        down = {}
        conn = self.zem.connect()
        try:
            curs = conn.cursor()
            query = ("SELECT device, component, count"
                    "  FROM status"
                    " WHERE eventClass = '%s'" % Status_OSProcess)
            if device:
                query += " AND device = '%s'" % device
            curs.execute(query)
            for device, component, count in curs.fetchall():
                down[device] = (component, count)
        finally:
            self.zem.close(conn)
        result = []
        for dev in self.config.devices():
            try:
                component, count = down[dev.id]
                result.append( (dev.id, component, count) )
            except KeyError:
                pass
        return result


    def getOSProcessConf(self, devices = None):
        'Get the OS Process configuration for all devices.'
        result = []
        for dev in self.config.devices():
            if devices and dev.id not in devices:
                continue
            dev = dev.primaryAq()
            try:
                procinfo = getOSProcessConf(dev)
                if procinfo:
                    result.append(procinfo)
            except POSError: raise
            except:
                self.log.exception("device %s", dev.id)
        return result


    def remote_getOSProcessConf(self, devices=None):
        return self.getOSProcessConf(devices)


    def remote_getProcessStatus(self, devices=None):
        return self.getProcessStatus(devices)


    def getDeviceConfig(self, device):
        return getOSProcessConf(device)


    def sendDeviceConfig(self, listener, config):
        return listener.callRemote('updateDevice', config)



