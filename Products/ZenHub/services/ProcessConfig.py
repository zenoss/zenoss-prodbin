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

import re
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
    regex = None
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
        for p in procs:
            regex = getattr(p.osProcessClass(), 'regex', False)
            if regex:
                try:
                    re.compile(regex)
                except sre_constants.error, ex:
                    log.warn("OS process class %s has an invalid regex (%s): %s",
                             p.getOSProcessClass(), regex, ex)
                    continue
            proc = ProcessProxy()
            proc.regex = regex
            proc.name = p.id
            proc.originalName = p.name()
            proc.ignoreParameters = (
                getattr(p.osProcessClass(), 'ignoreParameters', False))
            proc.restart = p.alertOnRestart()
            proc.severity = p.getFailSeverity()
            proc.processClass = p.getOSProcessClass()
            proxy.processes[p.id] = proc
            proxy.thresholds.extend(p.getThresholdInstances('SNMP'))

        if proxy.processes:
            return proxy

    @onUpdate(OSProcessClass, OSProcessOrganizer)
    def processTreeUpdated(self, object, event):
        self._reconfigureIfNotify(object)


if __name__ == '__main__':
    from Products.ZenHub.ServiceTester import ServiceTester
    tester = ServiceTester(ProcessConfig)
    def printer(config):
        for proc in config.processes.values():
            print '\t'.join([proc.name, proc.ignoreParameters, proc.regex])
    tester.printDeviceProxy = printer
    tester.showDeviceInfo()

