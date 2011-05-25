###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2010 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = '''CommandPerformanceConfig

Provides configuration to zencommand clients.
'''
import logging
log = logging.getLogger('zen.HubService.CommandPerformanceConfig')
import traceback

import Globals
from ZODB.POSException import ConflictError

from Products.ZenCollector.services.config import CollectorConfigService
from Products.ZenRRD.zencommand import Cmd, DataPointConfig
from Products.DataCollector.Plugins import getParserLoader
from Products.ZenEvents.ZenEventClasses import Error, Clear, Cmd_Fail


class CommandPerformanceConfig(CollectorConfigService):
    dsType = 'COMMAND'

    def __init__(self, dmd, instance):
        deviceProxyAttributes = ('zCommandPort',
                                 'zCommandUsername',
                                 'zCommandPassword',
                                 'zCommandLoginTimeout',
                                 'zCommandCommandTimeout',
                                 'zKeyPath',
                                 'zSshConcurrentSessions',
                                )
        CollectorConfigService.__init__(self, dmd, instance, 
                                        deviceProxyAttributes)

    # Use case: create a dummy device to act as a placeholder to execute commands
    #           So don't filter out devices that don't have IP addresses.

    def _getDsDatapoints(self, comp, ds, ploader, perfServer):
        """
        Given a component a data source, gather its data points
        """
        parser = ploader.create()
        points = []          
        component_name = ds.getComponent(comp)
        basepath = comp.rrdPath()
        for dp in ds.getRRDDataPoints():
            dpc = DataPointConfig()
            dpc.id = dp.id
            dpc.component = component_name
            dpc.rrdPath = "/".join((basepath, dp.name()))
            dpc.rrdType = dp.rrdtype
            dpc.rrdCreateCommand = dp.getRRDCreateCommand(perfServer)
            dpc.rrdMin = dp.rrdmin
            dpc.rrdMax = dp.rrdmax
            dpc.data = parser.dataForParser(comp, dp)
            points.append(dpc)

        return points

    def _getDsCycleTime(self, comp, templ, ds):
        cycleTime = 300
        try:
            cycleTime = int(ds.cycletime)
        except ValueError:
            message = "Unable to convert the cycle time '%s' to an " \
                          "integer for %s/%s on %s" \
                          " -- setting to 300 seconds" % (
                          ds.cycletime, templ.id, ds.id, comp.device().id)
            log.error(message)
            component = ds.getPrimaryUrlPath()
            dedupid = "Unable to convert cycletime for %s" % component
            self.sendEvent(dict(
                    device=comp.device().id, component=component,
                    eventClass='/Cmd', severity=Warning, summary=message,
                    dedupid=dedupid,  
            ))
        return cycleTime

    def _safeGetComponentConfig(self, comp, device, perfServer,
                                commands, thresholds):
        """
        Catchall wrapper for things not caught at previous levels
        """
        if not comp.monitorDevice():
            return None

        try:
            threshs = self._getComponentConfig(comp, device, perfServer, commands)
            if threshs:
                thresholds.extend(threshs)
        except ConflictError: raise
        except Exception, ex:
            msg = "Unable to process %s datasource(s) for device %s -- skipping" % (
                              self.dsType, device.id)
            log.exception(msg)
            details = dict(traceback=traceback.format_exc(),
                           msg=msg)
            self._sendCmdEvent(device.id, details)

    def _getComponentConfig(self, comp, device, perfServer, cmds):
        for templ in comp.getRRDTemplates():
            for ds in templ.getRRDDataSources(self.dsType):
                if not ds.enabled:
                    continue

                # Ignore SSH datasources if no username set
                useSsh = getattr(ds, 'usessh', False)
                if useSsh and not device.zCommandUsername:
                    self._warnUsernameNotSet(device)
                    continue

                parserName = getattr(ds, "parser", "Auto")
                ploader = getParserLoader(self.dmd, parserName)
                if ploader is None:
                    log.error("Could not load %s plugin", parserName)
                    continue

                cmd = Cmd()
                cmd.useSsh = useSsh
                cmd.name = "%s/%s" % (templ.id, ds.id)
                cmd.cycleTime = self._getDsCycleTime(comp, templ, ds)
                cmd.component = ds.getComponent(comp)
                cmd.eventClass = ds.eventClass
                cmd.eventKey = ds.eventKey or ds.id
                cmd.severity = ds.severity
                cmd.parser = ploader
                cmd.ds = ds.titleOrId()
                cmd.points = self._getDsDatapoints(comp, ds, ploader, perfServer)

                # If the datasource supports an environment dictionary, use it
                cmd.env = getattr(ds, 'env', None)

                try:
                    cmd.command = ds.getCommand(comp)
                except ConflictError: raise
                except Exception: # TALES error
                    msg = "TALES error for device %s datasource %s" % (
                               device.id, ds.id)
                    details = dict(
                           msg=msg,
                           template=templ.id,
                           datasource=ds.id,
                           affected_device=device.id,
                           affected_component=comp.id,
                           resolution='Could not create a command to send to zencommand' \
                                      ' because TALES evaluation failed.  The most likely' \
                                      ' cause is unescaped special characters in the command.' \
                                      ' eg $ or %')
                    # This error might occur many, many times
                    self._sendCmdEvent('localhost', details)
                    continue

                self.enrich(cmd, templ, ds)
                cmds.add(cmd)

        return comp.getThresholdInstances(self.dsType)

    def enrich(self, cmd, template, ds):
        """
        Hook routine available for subclassed services
        """
        pass

    def _createDeviceProxy(self, device):
        proxy = CollectorConfigService._createDeviceProxy(self, device)

        proxy.configCycleInterval = self._prefs.perfsnmpCycleInterval
        proxy.name = device.id
        proxy.device = device.id
        proxy.lastmodeltime = device.getLastChangeString()
        proxy.lastChangeTime = float(device.getLastChange())

        # Only send one event per warning type
        self._sentNoUsernameSetWarning = False
        self._sentNoUsernameSetClear = False

        perfServer = device.getPerformanceServer()
        commands = set()

        # First for the device....
        proxy.thresholds = []
        self._safeGetComponentConfig(device, device, perfServer,
                                commands, proxy.thresholds)

        # And now for its components
        for comp in device.getMonitoredComponents(collector='zencommand'):
            self._safeGetComponentConfig(comp, device, perfServer,
                                commands, proxy.thresholds)

        if commands:
            proxy.datasources = list(commands)
            return proxy
        return None

    def _sendCmdEvent(self, name, details=None):
        msg = 'zCommandUsername is not set so SSH-based commands will not run'
        ev = dict(
                device=name,
                eventClass=Cmd_Fail,
                eventKey='zCommandUsername',
                severity=Error,
                component='zencommand',
                summary=msg,
        )
        if details:
            ev.update(details)
        self.sendEvent(ev)

    def _warnUsernameNotSet(self, device):
        """
        Warn that the username is not set for device and the SSH command cannot be
        executed.
        """
        if self._sentNoUsernameSetWarning:
            return

        msg = 'zCommandUsername is not set so SSH-based commands will not run'
        name = device.titleOrId()
        log.error('%s for %s', msg, name)
        self._sendCmdEvent(name)
        self._sentNoUsernameSetWarning = True

    def _clearUsernameNotSet(self, device):
        if self._sentNoUsernameSetClear:
            return

        self._sendCmdEvent(device.titleOrId(), {'severity':Clear})
        self._sentNoUsernameSetClear = True

if __name__ == '__main__':
    from Products.ZenHub.ServiceTester import ServiceTester
    tester = ServiceTester(CommandPerformanceConfig)
    def printer(proxy):
        print '\t'.join([ '', 'Name', 'Use SSH?', 'CycleTime',
                         'Component', 'Points'])
        for cmd in sorted(proxy.datasources):
            print '\t'.join( map(str, [ '', cmd.name, cmd.useSsh,
                cmd.cycleTime, cmd.component, cmd.points ]) )
    tester.printDeviceProxy = printer
    tester.showDeviceInfo()

