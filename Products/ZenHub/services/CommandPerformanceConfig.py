##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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
from Products.ZenModel.OSProcess import OSProcess

_ZCOMMAND_USERNAME_NOT_SET = 'zCommandUsername is not set so SSH-based commands will not run'

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
        contextUUID = comp.getUUID()
        devuuid = comp.device().getUUID()
        componentId = comp.id
        for dp in ds.getRRDDataPoints():
            dpc = DataPointConfig()
            dpc.id = dp.id
            dpc.component = component_name
            dpc.contextUUID = contextUUID
            dpc.componentId = componentId
            dpc.dpName = dp.name()
            dpc.devuuid = devuuid
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
        except Exception:
            msg = "Unable to process %s datasource(s) for device %s -- skipping" % (
                              self.dsType, device.id)
            log.exception(msg)
            self._sendCmdEvent(device.id, msg, traceback=traceback.format_exc())

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

                if isinstance(comp, OSProcess):
                    # save off the regex's specified in the UI to later run
                    # against the processes running on the device
                    cmd.regex = comp.osProcessClass().regex
                    cmd.excludeRegex = comp.osProcessClass().excludeRegex
                    
                    # We need the comp.id in order to determine if a process matches
                    # a regex that has a name capture group
                    # see OSProcess.py ... method: generateId
                    cmd.componentId = comp.id

                # If the datasource supports an environment dictionary, use it
                cmd.env = getattr(ds, 'env', None)

                try:
                    cmd.command = ds.getCommand(comp)
                except Exception as ex: # TALES error
                    msg = "TALES error for device %s datasource %s" % (
                               device.id, ds.id)
                    details = dict(
                           template=templ.id,
                           datasource=ds.id,
                           affected_device=device.id,
                           affected_component=comp.id,
                           tb_exception=str(ex),
                           resolution='Could not create a command to send to zencommand' \
                                      ' because TALES evaluation failed.  The most likely' \
                                      ' cause is unescaped special characters in the command.' \
                                      ' eg $ or %')
                    # This error might occur many, many times
                    self._sendCmdEvent('localhost', msg, **details)
                    continue

                self.enrich(comp, cmd, templ, ds)
                cmds.add(cmd)

        return comp.getThresholdInstances(self.dsType)

    def enrich(self, comp, cmd, template, ds):
        """
        Hook routine available for subclassed services
        """
        pass

    def _createDeviceProxy(self, device):
        proxy = CollectorConfigService._createDeviceProxy(self, device)

        # Framework expects a default value but zencommand uses cycles per datasource instead
        proxy.configCycleInterval = 0

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

    def _sendCmdEvent(self, device, summary, eventClass=Cmd_Fail, severity=Error,
                      component='zencommand', **kwargs):
        ev = dict(
                device=device,
                eventClass=eventClass,
                severity=severity,
                component=component,
                summary=summary,
        )
        if kwargs:
            ev.update(kwargs)
        try:
            self.sendEvent(ev)
        except Exception:
            log.exception('Failed to send event: %r', ev)

    def _warnUsernameNotSet(self, device):
        """
        Warn that the username is not set for device and the SSH command cannot be
        executed.
        """
        if self._sentNoUsernameSetWarning:
            return

        name = device.titleOrId()
        log.error('%s for %s', _ZCOMMAND_USERNAME_NOT_SET, name)
        self._sendCmdEvent(name, _ZCOMMAND_USERNAME_NOT_SET,
            eventKey='zCommandUsername')
        self._sentNoUsernameSetWarning = True

    def _clearUsernameNotSet(self, device):
        if self._sentNoUsernameSetClear:
            return

        self._sendCmdEvent(device.titleOrId(), _ZCOMMAND_USERNAME_NOT_SET,
            eventKey='zCommandUsername', severity=Clear)
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
