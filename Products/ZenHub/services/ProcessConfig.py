##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import re
import sre_constants
import logging
log = logging.getLogger('zen.HubService.ProcessConfig')

import Globals

from Products.ZenCollector.services.config import CollectorConfigService
from Products.ZenUtils.Utils import unused
from Products.ZenCollector.services.config import DeviceProxy
from Products.ZenEvents import Event
from Products.ZenModel.OSProcessClass import OSProcessClass
from Products.ZenModel.OSProcessOrganizer import OSProcessOrganizer
from Products.ZenHub.zodb import onUpdate
from Products.Zuul.interfaces import ICatalogTool
unused(DeviceProxy)

from twisted.spread import pb

class ProcessProxy(pb.Copyable, pb.RemoteCopy):
    """
    Track process-specific configuration data
    """
    name = None
    originalName = None
    restart = None
    regex = None
    excludeRegex = None
    severity = Event.Warning
    cycleTime = None
    processClass = None

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
            log.debug("Device %s has no monitored processes -- ignoring",
                      device.titleOrId())
            return None

        proxy = CollectorConfigService._createDeviceProxy(self, device)
        proxy.configCycleInterval = self._prefs.processCycleInterval

        proxy.name = device.id
        proxy.lastmodeltime = device.getLastChangeString()
        proxy.thresholds = []
        proxy.processes = {}
        proxy.snmpConnInfo = device.getSnmpConnInfo()
        devuuid = device.getUUID()
        for p in procs:
            # Find out which datasources are responsible for this process
            # if SNMP is not responsible, then do not add it to the list
            snmpMonitored = False
            for rrdTpl in p.getRRDTemplates():
                if len(rrdTpl.getRRDDataSources("SNMP")) > 0:
                    snmpMonitored = True
                    break

            # In case the process is not SNMP monitored
            if not snmpMonitored:
                log.debug("Skipping process %r - not an SNMP monitored process", p)
                continue
            # In case the catalog is out of sync above
            if not p.monitored():
                log.debug("Skipping process %r - zMonitor disabled", p)
                continue
            regex = getattr(p.osProcessClass(), 'regex', False)
            excludeRegex = getattr(p.osProcessClass(), 'excludeRegex', False)
            
            if regex:
                try:
                    re.compile(regex)
                except sre_constants.error, ex:
                    log.warn("OS process class %s has an invalid regex (%s): %s",
                             p.getOSProcessClass(), regex, ex)
                    continue
            else:
                log.warn("OS process class %s has no defined regex, this process not being monitored",
                         p.getOSProcessClass())
                continue

            proc = ProcessProxy()
            proc.contextUUID = p.getUUID()
            proc.deviceuuid = devuuid
            proc.regex = regex
            proc.excludeRegex = excludeRegex
            proc.name = p.id
            proc.originalName = p.name()
            proc.restart = p.alertOnRestart()
            proc.severity = p.getFailSeverity()
            proc.processClass = p.getOSProcessClass()
            proxy.processes[p.id] = proc
            proxy.thresholds.extend(p.getThresholdInstances('SNMP'))

        if proxy.processes:
            return proxy

    @onUpdate(OSProcessClass)
    def processClassUpdated(self, object, event):
        devices = set()
        for process in object.instances():
            device = process.device()
            if not device:
                continue
            device = device.primaryAq()
            device_path = device.getPrimaryUrlPath()
            if not device_path in devices:
                self._notifyAll(device)
                devices.add(device_path)

    @onUpdate(OSProcessOrganizer)
    def processOrganizerUpdated(self, object, event):
        catalog = ICatalogTool(object.primaryAq())
        results = catalog.search(OSProcessClass)
        if not results.total:
            return
        devices = set()
        for organizer in results:
            if results.areBrains:
                organizer = organizer.getObject()
            for process in organizer.instances():
                device = process.device()
                if not device:
                    continue
                device = device.primaryAq()
                device_path = device.getPrimaryUrlPath()
                if not device_path in devices:
                    self._notifyAll(device)
                    devices.add(device_path)


if __name__ == '__main__':
    from Products.ZenHub.ServiceTester import ServiceTester
    tester = ServiceTester(ProcessConfig)
    def printer(config):
        for proc in config.processes.values():
            print '\t'.join([proc.name, str(proc.regex)])
    tester.printDeviceProxy = printer
    tester.showDeviceInfo()
