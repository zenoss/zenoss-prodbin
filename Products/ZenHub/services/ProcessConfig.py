###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

#from Products.ZenRRD.zenprocess import Process
from Products.ZenCollector.services.config import CollectorConfigService
from Products.ZenEvents.ZenEventClasses import Status_Snmp

from Products.ZenUtils.Utils import unused
from Products.ZenCollector.services.config import DeviceProxy
from Products.ZenEvents import Event
unused(DeviceProxy)

from twisted.spread import pb

class ProcessProxy(pb.Copyable, pb.RemoteCopy):
    """
    Track process-specific configuration data
    """
    name = None
    originalName = None
    ignoreParameters = False
    restart = None
    severity = Event.Warning
    status = 0
    cycleTime = None

    def __init__(self):
        pass

    def __str__(self):
        """
        Override the Python default to represent ourselves as a string
        """
        return str(self.name)
    __repr__ = __str__


pb.setUnjellyableForClass(ProcessProxy, ProcessProxy)


class ProcessConfig(CollectorConfigService):

    def __init__(self, dmd, instance):
        deviceProxyAttributes = ('zMaxOIDPerRequest',)
        CollectorConfigService.__init__(self, dmd, instance, deviceProxyAttributes)

    def _filterDevice(self, device):
        include = CollectorConfigService._filterDevice(self, device)
        include = include and device.snmpMonitorDevice()
            
        return include

    def _createDeviceProxy(self, device):
        procs = device.getMonitoredComponents(collector='zenprocess')
        if not procs:
            return None

        proxy = CollectorConfigService._createDeviceProxy(self, device)
        proxy.configCycleInterval = self._prefs.processCycleInterval

        proxy.name = device.id
        proxy.thresholds = []
        proxy.processes = {}
        proxy.snmpConnInfo = device.getSnmpConnInfo()
        for p in procs:
            proxy.thresholds.extend(p.getThresholdInstances('SNMP'))
            proc = ProcessProxy()
            proc.name = p.id
            proc.originalName = p.name()
            proc.ignoreParameters = (
                getattr(p.osProcessClass(), 'ignoreParameters', False))
            proc.restart = p.alertOnRestart()
            proc.severity = p.getFailSeverity()
            proxy.processes[p.id] = proc

        return proxy

    def _postCreateDeviceProxy(self, deviceConfigs):
        deviceIdList = [ [d.id, d] for d in deviceConfigs]
        deviceProxies = dict(deviceIdList)
        
        self._updateSnmpStatus(deviceProxies)

    def _updateSnmpStatus(self, deviceProxyMap):
        """
        update the device proxies with their snmp status
        
        @parameter deviceProxyMap: dict of device id to DeviceProxy
        @type deviceProxyMap: dict of {string, DeviceProxy}
        """
        devName = None
        if len(deviceProxyMap) == 1:
            devName = deviceProxyMap.values()[0].id
        snmpStatuses = self._getSnmpStatus(devName)
        for name, count in snmpStatuses:
            deviceConfig = deviceProxyMap.get(name)
            if deviceConfig:
                deviceConfig.snmpStatus = count
                
    
    def _updateProcessStatus(self, deviceProxyMap):
        """
        update the processes of device proxies with their snmp status
        
        @parameter deviceProxyMap: dict of device id to DeviceProxy
        @type deviceProxyMap: dict of {string, DeviceProxy}
        """
        devName = None
        if len(deviceProxyMap) == 1:
            devName = deviceProxyMap.values()[0].id
        procStatuses = self._getProcessStatus(devName)
        down = {}
        for device, component, count in procStatuses:
            down[ (device, component) ] = count
        for name, device in deviceProxyMap.items():
            for proc in device.processes.values():
                proc.status = down.get( (name, proc.originalName), 0)

    def _getSnmpStatus(self, devname=None):
        "Return the failure counts for Snmp" 
        counts = {}
        try:
            # get all the events with /Status/Snmp
            conn = self.zem.connect()
            try:
                curs = conn.cursor()
                cmd = ('SELECT device, sum(count)  ' +
                       '  FROM status ' +
                       ' WHERE eventClass = "%s"' % Status_Snmp)
                if devname:
                    cmd += ' AND device = "%s"' % devname
                cmd += ' GROUP BY device'
                curs.execute(cmd);
                counts = dict([(d, int(c)) for d, c in curs.fetchall()])
            finally:
                self.zem.close(conn)
        except Exception:
            self.log.exception('Unable to get Snmp Status')
            raise
        if devname:
            return [(devname, counts.get(devname, 0))]
        return [(dev.id, counts.get(dev.id, 0)) for dev in self.config.devices()]
    def _getProcessStatus(self, device=None):
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

