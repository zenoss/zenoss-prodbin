##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import importlib
import logging
from pprint import pformat
import re
import sys
import time
import traceback

from twisted.spread import pb
from twisted.internet import defer, task
from twisted.internet.threads import deferToThread

from Products.ZenRRD.zencommand import Cmd, DataPointConfig
from Products.ZenUtils.Utils import importClass
from Products.DataCollector.DeviceProxy import DeviceProxy as ModelDeviceProxy
from Products.ZenCollector.services.config import DeviceProxy
from Products.ZenHub.PBDaemon import RemoteException
from Products.ZenHub.services.Procrastinator import Procrastinate
from Products.ZenUtils.debugtools import profile

from ZenPacks.zenoss.PythonCollector.datasources.PythonDataSource \
    import PythonDataSource
from ZenPacks.zenoss.PythonCollector.services.PythonConfig \
    import PythonDataSourceConfig

from Products.ZenHub.services.SnmpPerformanceConfig import SnmpDeviceProxy, get_component_manage_ip
from Products.ZenHub.services.PerformanceConfig import SnmpConnInfo

from .utils import replace_prefix, all_parent_dcs
from .utils.tales import talesEvalStr
from .applydatamapper import ApplyDataMapper
from .db import get_db
from .modelevents import onZenPackAdapterDeviceUpdate, onZenPackAdapterDeviceAdd, onZenPackAdapterDeviceDelete

log = logging.getLogger('zen.zminihub.services')


def translateError(callable):
    """
    Decorator function to wrap remote exceptions into something
    understandable by our daemon.

    @parameter callable: function to wrap
    @type callable: function
    @return: function's return or an exception
    @rtype: various
    """
    def inner(*args, **kw):
        """
        Interior decorator
        """
        try:
            return callable(*args, **kw)
        except Exception, ex:
            log.exception(ex)
            raise RemoteException(
                'Remote exception: %s: %s' % (ex.__class__, ex),
                traceback.format_exc())
    return inner


class ZenPackAdapterService(pb.Referenceable):

    def __init__(self):
        self.log = log
        self.listeners = []
        self.listenerOptions = {}
        self.callTime = 0
        self.db = get_db()

    def remoteMessageReceived(self, broker, message, args, kw):
        self.log.debug("Servicing %s in %s", message, self.name())
        now = time.time()
        try:
            return pb.Referenceable.remoteMessageReceived(
                self, broker, message, args, kw
            )
        finally:
            secs = time.time() - now
            self.log.debug("Time in %s: %.2f", message, secs)
            self.callTime += secs

    def name(self):
        return self.__class__.__name__

    def addListener(self, remote, options=None):
        remote.notifyOnDisconnect(self.removeListener)
        self.log.info(
            "adding listener for %s", self.name()
        )
        self.listeners.append(remote)
        if options:
            self.listenerOptions[remote] = options

    def removeListener(self, listener):
        self.log.info(
            "removing listener for %s", self.name()
        )
        try:
            self.listeners.remove(listener)
        except ValueError:
            self.warning("Unable to remove listener... ignoring")

        self.listenerOptions.pop(listener, None)

    def sendEvents(self, events):
        if events:
            self.db.publish_events(events)

    def sendEvent(self, event, **kw):
        if event:
            if isinstance(event, list):
                self.sendEvents(event)
            elif isinstance(event, dict):
                self.sendEvents([event])
            else:
                self.log.debug("Unknown event type: {}".format(event))

    @translateError
    def remote_propertyItems(self):
        return [
            ('eventlogCycleInterval', 60),
            ('processCycleInterval', 180),
            ('statusCycleInterval', 60),
            ('winCycleInterval', 60),
            ('wmibatchSize', 10),
            ('wmiqueryTimeout', 100),
            ('configCycleInterval', 360),
            ('zenProcessParallelJobs', 10),
            ('pingTimeOut', 1.5),
            ('pingTries', 2),
            ('pingChunk', 75),
            ('pingCycleInterval', 60),
            ('maxPingFailures', 1440),
            ('modelerCycleInterval', 720),
            ('discoveryNetworks', ()),
            ('ccBacked', 1),
            ('description', ''),
            ('poolId', 'default'),
            ('iprealm', 'default'),
            ('renderurl', '/zport/RenderServer'),
            ('defaultRRDCreateCommand', (
                'RRA:AVERAGE:0.5:1:600',
                'RRA:AVERAGE:0.5:6:600',
                'RRA:AVERAGE:0.5:24:600',
                'RRA:AVERAGE:0.5:288:600',
                'RRA:MAX:0.5:6:600',
                'RRA:MAX:0.5:24:600',
                'RRA:MAX:0.5:288:600'))
        ]


class EventService(ZenPackAdapterService):

    def remote_sendEvent(self, evt):
        if evt:
            self.sendEvent(evt)

    def remote_sendEvents(self, evts):
        if evts:
            self.sendEvents(evts)

    def remote_getDevicePingIssues(self, *args, **kwargs):
        return None

    def remote_getDeviceIssues(self, *args, **kwargs):
        return None

    def remote_getDefaultPriority(self):
        return 3


class ModelerService(ZenPackAdapterService):

    @translateError
    def remote_getThresholdClasses(self):
        return []

    @translateError
    def remote_getCollectorThresholds(self):
        return []

    @translateError
    def remote_getClassCollectorPlugins(self):
        result = []
        for dc_name, dc in self.db.device_classes.iteritems():
            localPlugins = dc.zProperties.get('zCollectorPlugins', False)
            if not localPlugins:
                continue
            result.append((dc_name, localPlugins))
        return result

    @translateError
    def remote_getDeviceConfig(self, names, checkStatus=False):
        result = []
        for id in names:
            device = self.db.devices.get(id)
            if not device:
                continue

            proxy = ModelDeviceProxy()
            proxy.id = id
            proxy.skipModelMsg = ''
            proxy.manageIp = device.manageIp
            proxy.plugins = []
            proxy._snmpLastCollection = 0
            proxy._snmpStatus = 0


            plugin_ids = device.getProperty('zCollectorPlugins')
            for plugin_id in plugin_ids:
                plugin = self.db.modelerplugin.get(plugin_id)
                if not plugin:
                    continue

                proxy.plugins.append(plugin.pluginLoader)
                for pid in plugin.deviceProperties:
                    # zproperties
                    if device.hasProperty(pid):
                        setattr(proxy, pid, device.getProperty(pid))

                    # modeled properties (TODO- convert to use zobject for this)
                    elif hasattr(device, pid):
                        setattr(proxy, pid, getattr(device, pid))

                    # special cases
                    elif pid == '_snmpStatus' or pid == '_snmpLastCollection':
                        continue

                    else:
                        self.log.error("device property %s not found on %s", pid, id)

            result.append(proxy)

        return result

    @translateError
    def remote_getDeviceListByMonitor(self, monitor=None):
        return [x.id for x in self.db.devices]

    @translateError
    def remote_getDeviceListByOrganizer(self, organizer, monitor=None, options=None):
        dc = replace_prefix(organizer, "/Devices", "/")
        if dc not in self.db.device_classes:
            return []
        return [x.id for x in self.db.child_devices[dc]]

    @translateError
    def remote_applyDataMaps(self, device, maps, devclass=None, setLastCollection=False):
        mapper = self.db.get_mapper(device)
        schemaversion = mapper.schemaversion

        adm = ApplyDataMapper(mapper, self.db.devices[device])
        changed = False
        for datamap in maps:
            if adm.applyDataMap(device, datamap):
                changed = True

        self.log.debug("ApplyDataMaps Completed: New DataMapper: %s", pformat(mapper.objects))
        self.log.debug("ApplyDataMaps Changed: %s", changed)
        self.log.debug("ApplyDataMaps  schemaversion: %d -> %d", schemaversion, mapper.schemaversion)

        self.db.snapshot_device(device)

        return changed

    remote_singleApplyDataMaps = remote_applyDataMaps

    @translateError
    def remote_setSnmpLastCollection(self, device):
        return

    @translateError
    def remote_setSnmpConnectionInfo(self, device, version, port, community):
        return


class CollectorConfigService(ZenPackAdapterService):
    def __init__(self, deviceProxyAttributes=()):
        """
        Constructs a new CollectorConfig instance.

        Subclasses must call this __init__ method but cannot do so with
        the super() since parents of this class are not new-style classes.

        @param deviceProxyAttributes: a tuple of names for device attributes
               that should be copied to every device proxy created
        @type deviceProxyAttributes: tuple
        """
        ZenPackAdapterService.__init__(self)

        self._deviceProxyAttributes = ('id', 'manageIp',) + deviceProxyAttributes
        self.db = get_db()
        self.procrastinator = Procrastinate(self.pushConfig)
        self.last_schemaversion = {}

        # push configs down to the collectors when the models change.
        # (every 15 minutes)
        l = task.LoopingCall(self.pushConfigsIfNeeded)
        def err(reason):
            log.error("Error in pushConfigsIfNeeded LoopingCall: %s" % reason)
        l.start(15*60, now=False).addErrback(err)

    def _wrapFunction(self, functor, *args, **kwargs):
        """
        Call the functor using the arguments, and trap any unhandled exceptions.

        @parameter functor: function to call
        @type functor: method
        @parameter args: positional arguments
        @type args: array of arguments
        @parameter kwargs: keyword arguments
        @type kwargs: dictionary
        @return: result of functor(*args, **kwargs) or None if failure
        @rtype: result of functor
        """
        try:
            return functor(*args, **kwargs)
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception, ex:
            msg = 'Unhandled exception in zenhub service %s: %s' % (
                self.__class__, str(ex))
            self.log.exception(msg)

        return None

    @translateError
    def remote_getConfigProperties(self):
        return self.remote_propertyItems()

    @translateError
    def remote_getDeviceNames(self, options=None):
        # (note, this should be filtered by _filterDevices)
        return [x.id for x in self.db.devices]

    @translateError
    def remote_getDeviceConfigs(self, deviceNames=None, options=None):
        # (note, the device list should be filtered)

        if deviceNames is None or len(deviceNames) == 0:
            deviceNames = self.db.devices.keys()

        deviceConfigs = []
        for deviceName in deviceNames:
            device = self.db.get_zobject(device=deviceName)
            if device is None:
                log.error("Device ID %s not found", deviceName)
                continue

            proxies = self._wrapFunction(self._createDeviceProxies, device)
            if proxies:
                deviceConfigs.extend(proxies)

        return deviceConfigs

    @translateError
    def remote_getEncryptionKey(self):
        # if we actually use it, this should be persisted, not changed
        # every time.
        from cryptography.fernet import Fernet
        import hashlib
        import base64

        key = Fernet.generate_key()

        # Hash the key with the daemon identifier to get unique key per collector daemon
        s = hashlib.sha256()
        s.update(key)
        s.update(self.__class__.__name__)
        return base64.urlsafe_b64encode(s.digest())

    @translateError
    def remote_getThresholdClasses(self):
        return []

    @translateError
    def remote_getCollectorThresholds(self):
        return []

    def _createDeviceProxies(self, device):
        proxy = self._createDeviceProxy(device)
        return (proxy,) if (proxy is not None) else ()

    def _createDeviceProxy(self, device, proxy=None):
        """
        Creates a device proxy object that may be copied across the network.

        Subclasses should override this method, call it for a basic DeviceProxy
        instance, and then add any additional data to the proxy as their needs
        require.

        @param device: the regular device zobject to create a proxy from
        @return: a new device proxy object, or None if no proxy can be created
        @rtype: DeviceProxy
        """
        proxy = proxy if (proxy is not None) else DeviceProxy()

        # copy over all the attributes requested
        for attrName in self._deviceProxyAttributes:
            if hasattr(device, attrName):
                setattr(proxy, attrName, getattr(device, attrName, None))
            elif device.hasProperty(attrName):
                setattr(proxy, attrName, device.getProperty(attrName))

        return proxy

    @onZenPackAdapterDeviceDelete(str)
    def deviceDeleted(self, deviceId, event):
        self.procrastinator.doLater(deviceId) # -> pushConfig

    @onZenPackAdapterDeviceAdd(str)
    def deviceAdded(self, deviceId, event):
        self.procrastinator.doLater(deviceId) # -> pushConfig

    @onZenPackAdapterDeviceUpdate(str)
    def deviceUpdated(self, deviceId, event):
        self.procrastinator.doLater(deviceId) # -> pushConfig

    @defer.inlineCallbacks
    def pushConfig(self, deviceId):
        deferreds = []
        log.info("pushConfig self=%s, deviceId=%s, listeners=%s", self, deviceId, self.listeners)
        device = self.db.devices.get(deviceId, None)
        if device is None:
            for listener in self.listeners:
                log.info('  Performing remote call to delete device %s', deviceId)
                deferreds.append(listener.callRemote('deleteDevice', deviceId))
        else:
            proxy = yield deferToThread(self._createDeviceProxy, device)

            for listener in self.listeners:
                log.info('  Performing remote call to update device %s (proxy=%s)', deviceId, proxy)
                deferreds.append(listener.callRemote('updateDeviceConfig', proxy))

        yield defer.DeferredList(deferreds)

    def pushConfigsIfNeeded(self):
        log.info("Checking for model changes on %s" % self)
        deferreds = []
        for deviceId in self.db.devices:
            mapper = self.db.get_mapper(deviceId)

            # If components have been added, removed, or links between
            # them changed, the mapper schemaversion is incremented, and
            # we know that it is time to regenerate the config.
            last_schemaversion = self.last_schemaversion.get(deviceId)
            if mapper and mapper.schemaversion != last_schemaversion:
                self.last_schemaversion[deviceId] = mapper.schemaversion
                log.info("  Model for %s has changed.  Pushing new configs", deviceId)

                deferreds.append(self.pushConfig(deviceId))

        return defer.DeferredList(deferreds)


class CommandPerformanceConfig(CollectorConfigService):
    dsType = 'COMMAND'

    def __init__(self):
        deviceProxyAttributes = (
            'zCommandPort',
            'zCommandUsername',
            'zCommandPassword',
            'zCommandLoginTimeout',
            'zCommandCommandTimeout',
            'zKeyPath',
            'zSshConcurrentSessions',
        )
        CollectorConfigService.__init__(self, deviceProxyAttributes)

    def _createDeviceProxy(self, device, proxy=None):
        proxy = CollectorConfigService._createDeviceProxy(
            self, device, proxy=proxy)

        # Framework expects a default value but zencommand uses cycles per datasource instead
        proxy.configCycleInterval = 0

        proxy.name = device.id
        proxy.device = device.id
        proxy.lastmodeltime = "n/a"
        proxy.lastChangeTime = float(0)

        commands = set()

        # First for the device....
        proxy.thresholds = []

        self._safeGetComponentConfig(device, commands)

        # And now for its components
        for component in device.getMonitoredComponents(collector='zencommand'):
            self._safeGetComponentConfig(component, commands)

        if commands:
            proxy.datasources = list(commands)
            return proxy
        return None

    def _safeGetComponentConfig(self, deviceOrComponent, commands):
        """
        Catchall wrapper for things not caught at previous levels
        """

        try:
            self._getComponentConfig(deviceOrComponent, commands)
        except Exception:
            msg = "Unable to process %s datasource(s) for device %s -- skipping" % (
                self.dsType, deviceOrComponent.device().id)
            log.exception(msg)

    def _getComponentConfig(self, deviceOrComponent, cmds):
        for templ in deviceOrComponent.getRRDTemplates():
            for ds in templ.getRRDDataSources(self.dsType):

                # Ignore SSH datasources if no username set
                useSsh = getattr(ds, 'usessh', False)
                if useSsh and not device.getProperty('zCommandUsername'):
                    log.warning("Username not set on device %s" % device)
                    continue

                parserName = getattr(ds, "parser", "Auto")
                plugin = self.db.parserplugin.get(parserName)
                if plugin is None:
                    log.error("Could not find %s parser plugin", parserName)
                    continue
                ploader = plugin.pluginLoader

                cmd = Cmd()
                cmd.useSsh = useSsh
                cmd.name = "%s/%s" % (templ.id, ds.id)
                cmd.cycleTime = self._getDsCycleTime(device, templ, ds)
                cmd.component = deviceOrComponent.titleOrId()

                # TODO: events are not supported currently.
                # cmd.eventClass = ds.eventClass
                # cmd.eventKey = ds.eventKey or ds.id
                # cmd.severity = ds.severity
                cmd.parser = ploader
                cmd.ds = ds.id
                cmd.points = self._getDsDatapoints(deviceOrComponent, ds, ploader)

                # TODO: OSProcess component monitoring isn't supported currently.
                # if isinstance(comp, OSProcess):
                #     # save off the regex's specified in the UI to later run
                #     # against the processes running on the device
                #     cmd.includeRegex = component.includeRegex
                #     cmd.excludeRegex = component.excludeRegex
                #     cmd.replaceRegex = component.replaceRegex
                #     cmd.replacement  = component.replacement
                #     cmd.primaryUrlPath = component.processClassPrimaryUrlPath()
                #     cmd.generatedId = component.id
                #     cmd.displayName = component.displayName
                #     cmd.sequence = component.osProcessClass().sequence

                # If the datasource supports an environment dictionary, use it
                cmd.env = getattr(ds, 'env', None)

                try:
                    cmd.command = ds.getCommand(deviceOrComponent)
                except Exception as ex:  # TALES error
                    details = dict(
                        template=templ.id,
                        datasource=ds.id,
                        affected_device=deviceOrComponent.device().id,
                        affected_component=deviceOrComponent.id,
                        tb_exception=str(ex),
                        resolution='Could not create a command to send to zencommand' +
                                   ' because TALES evaluation failed.  The most likely' +
                                   ' cause is unescaped special characters in the command.' +
                                   ' eg $ or %')
                    # This error might occur many, many times
                    log.warning("Event: %s", str(details))
                    continue

                cmds.add(cmd)

    def _getDsDatapoints(self, deviceOrComponent, ds, ploader):
        """
        Given a component a data source, gather its data points
        """
        parser = ploader.create()
        points = []
        for dp_id, dp in ds.datapoints.iteritems():
            dpc = DataPointConfig()
            dpc.id = dp_id
            dpc.component = deviceOrComponent.titleOrId()
            dpc.dpName = dp_id
            dpc.data = self._dataForParser(parser, deviceOrComponent, dp_id, dp)

            dpc.rrdPath = '/'.join((deviceOrComponent.rrdPath(), dp_id))
            dpc.metadata = deviceOrComponent.getMetricMetadata()
            # by default, metrics have the format <device id>/<metric name>.
            # Setting this to the datasource id, gives us ds/dp, which
            # the cloud metric publisher turns into ds_dp.  So it's important
            # for each collector daemon / config service to make sure that
            # its metrics do get formatted that way.
            dpc.metadata['metricPrefix'] = ds.id

            points.append(dpc)

        return points

    def _dataForParser(self, parser, comp, dpId, dp):
        # LIMIT: Normally, this is a method on the parser, and its behavior
        # can be overridden to supply arbitrary model information to the parser

        if hasattr(parser, 'componentScanValue'):
            if parser.componentScanValue == 'id':
                return {'componentScanValue': comp.id}
            else:
                return {'componentScanValue': getattr(comp, parser.componentScanValue)}

        return {}

    def _getDsCycleTime(self, device, templ, ds):
        cycleTime = 300
        try:
            cycleTime = int(ds.getCycleTime(device))
        except ValueError:
            message = "Unable to convert the cycle time '%s' to an " \
                      "integer for %s/%s on %s" \
                      " -- setting to 300 seconds" % (
                          ds.cycletime, templ.id, ds.id, device.id)
            log.error(message)
        return cycleTime


class PythonConfig(CollectorConfigService):

    def __init__(self, modelerService):
        CollectorConfigService.__init__(self)
        self.modelerService = modelerService
        self.python_sourcetypes = set()
        for sourcetype, dsinfo in self.db.datasource.iteritems():
            dsClass = importClass(dsinfo.modulename, dsinfo.classname)
            if issubclass(dsClass, PythonDataSource):
                self.python_sourcetypes.add(sourcetype)

    # @profile
    def _createDeviceProxy(self, device):
        proxy = CollectorConfigService._createDeviceProxy(self, device)
        proxy.datasources = list(self._datasources(device))

        for component in device.getMonitoredComponents():
            proxy.datasources += list(
                self._datasources(component))

        if len(proxy.datasources) > 0:
            return proxy

        return None

    def _datasources(self, deviceOrComponent):
        known_point_properties = (
            'isrow', 'rrdmax', 'description', 'rrdmin', 'rrdtype', 'createCmd', 'tags')

        device = deviceOrComponent.device()

        for template in deviceOrComponent.getRRDTemplates():
            # Get all enabled datasources that are PythonDataSource or
            # subclasses thereof.
            datasources = [ds for ds in template.getRRDDataSources()
                           if ds.sourcetype in self.python_sourcetypes]

            for ds in datasources:
                datapoints = []

                if 'ZenPacks.zenoss.CalculatedPerformance' in ds.plugin_classname:
                    # CalcPerf isn't supported.
                    continue


                try:
                    ds_plugin_class = self._getPluginClass(ds)
                except Exception as e:
                    log.error(
                        "Failed to load plugin %r for %s/%s: %s",
                        getattr(ds, 'plugin_classname', '[unknown]'),
                        template.id,
                        ds.id,
                        e)

                    continue

                for dp_id, dp in ds.datapoints.iteritems():
                    dp_config = DataPointConfig()

                    dp_config.id = dp_id
                    dp_config.dpName = dp_id
                    dp_config.rrdType = dp.rrdtype

                    dp_config.rrdPath = '/'.join((deviceOrComponent.rrdPath(), dp_id))
                    dp_config.metadata = deviceOrComponent.getMetricMetadata()

                    # by default, metrics have the format <device id>/<metric name>.
                    # Setting this to the datasource id, gives us ds/dp, which
                    # the cloud metric publisher turns into ds_dp.  So it's important
                    # for each collector daemon / config service to make sure that
                    # its metrics do get formatted that way.
                    dp_config.metadata['metricPrefix'] = ds.id

                    # Attach unknown properties to the dp_config
                    for key in dp.__dict__.keys():
                        if key in known_point_properties:
                            continue
                        try:
                            value = getattr(dp, key)
                            if isinstance(value, basestring) and '$' in value:
                                extra = {
                                    'device': device,
                                    'dev': device,
                                    'devname': device.id,
                                    'datasource': ds,
                                    'ds': ds,
                                    'datapoint': dp,
                                    'dp': dp,
                                }

                                value = talesEvalStr(
                                    value,
                                    deviceOrComponent,
                                    extra=extra)

                            setattr(dp_config, key, value)
                        except Exception:
                            pass

                    datapoints.append(dp_config)

                ds_config = PythonDataSourceConfig()
                ds_config.device = device.id
                ds_config.manageIp = device.manageIp
                ds_config.component = deviceOrComponent.id
                ds_config.plugin_classname = ds.plugin_classname
                ds_config.template = template.id
                ds_config.datasource = ds.id
                ds_config.config_key = self._getConfigKey(ds, deviceOrComponent)
                ds_config.params = self._getParams(ds, deviceOrComponent)
                ds_config.cycletime = ds.getCycleTime(deviceOrComponent)
                # ds_config.eventClass = ds.eventClass
                # ds_config.eventKey = ds.eventKey
                ds_config.eventKey = ""
                # ds_config.severity = ds.severity
                ds_config.points = datapoints

                # Populate attributes requested by plugin.
                for attr in ds_plugin_class.proxy_attributes:
                    value = getattr(deviceOrComponent, attr, None)
                    if callable(value):
                        value = value()

                    setattr(ds_config, attr, value)

                yield ds_config

    def _getPluginClass(self, ds):
        """Return plugin class referred to by self.plugin_classname."""

        class_parts = ds.plugin_classname.split('.')
        module_name = '.'.join(class_parts[:-1])
        class_name = class_parts[-1]
        if module_name not in sys.modules:
            importlib.import_module(module_name)

        return getattr(sys.modules[module_name], class_name)

    def _getConfigKey(self, ds, context):
        """Returns a tuple to be used to split configs at the collector."""
        if not ds.plugin_classname:
            return [context.id]

        try:
            return self._getPluginClass(ds).config_key(ds, context)
        except Exception as ex:
            log.error("Error getting config key for ds %s, context %s: %s", ds, context, ex)
            return None

    def _getParams(self, ds, context):
        """Returns extra parameters needed for collecting this datasource."""
        if not ds.plugin_classname:
            return {}

        try:
            params = self._getPluginClass(ds).params(ds, context)
        except Exception as ex:
            log.error("Error getting params for ds %s, context %s: %s", ds, context, ex)
            params = {}

        return params

    def remote_applyDataMaps(self, device, datamaps):
        return self.modelerService.remote_applyDataMaps(device, datamaps)


class SnmpPerformanceConfig(CollectorConfigService):
    def __init__(self):
        deviceProxyAttributes = (
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
            'zSnmpCollectionInterval',
        )
        CollectorConfigService.__init__(self, deviceProxyAttributes)

    # def _filterDevice(self, device):
    #     include = CollectorConfigService._filterDevice(self, device)

    #     if getattr(device, 'zSnmpMonitorIgnore', False):
    #         self.log.debug("Device %s skipped because zSnmpMonitorIgnore is True",
    #                        device.id)
    #         include = False

    #     if not device.getManageIp():
    #         self.log.debug("Device %s skipped because its management IP address is blank.",
    #                        device.id)
    #         include = False

    #     return include


    def _transform_oid(self, oid, comp):
        """lookup the index"""
        index = None
        snmpindex_dct = getattr(comp, "snmpindex_dct", None)
        if snmpindex_dct is not None:
            for prefix, index_ in snmpindex_dct.iteritems():
                if oid.startswith(prefix):
                    index = index_
                    break
        if index is None:
            index = getattr(comp, "ifindex", comp.snmpindex)
        return "{0}.{1}".format(oid, index) if index else oid


    def _getComponentConfig(self, comp, oids):
        """
        SNMP components can build up the actual OID based on a base OID and
        the snmpindex of the component.
        """
        if comp.snmpIgnore():
            return None

        validOID = re.compile(r'(?:\.?\d+)+$')
        metadata = comp.getMetricMetadata()
        for templ in comp.getRRDTemplates():
            for ds in templ.getRRDDataSources("SNMP"):
                if not ds.oid:
                    continue

                oid = self._transform_oid(ds.oid.strip("."), comp)
                if not oid:
                    log.warn("The data source %s OID is blank -- ignoring", ds.id)
                    continue
                elif not validOID.match(oid):
                    oldOid = oid
                    oid = self.dmd.Mibs.name2oid(oid)
                    if not oid:
                        msg =  "The OID %s is invalid -- ignoring" % oldOid
                        self.sendEvent(dict(
                            device=comp.device().id, component=ds.getPrimaryUrlPath(),
                            eventClass='/Status/Snmp', severity=Warning, summary=msg,
                        ))
                        continue

                for dp_id, dp in ds.datapoints.iteritems():
                    cname = comp.id
                    dp_metadata = dict(metadata)
                    # by default, metrics have the format <device id>/<metric name>.
                    # Setting this to the datasource id, gives us ds/dp, which
                    # the cloud metric publisher turns into ds_dp.  So it's important
                    # for each collector daemon / config service to make sure that
                    # its metrics do get formatted that way.
                    dp_metadata['metricPrefix'] = ds.id

                    oidData = (
                        cname,
                        dp_id,
                        dp.rrdtype,
                        '',
                        dp.rrdmin,
                        dp.rrdmax,
                        dp_metadata,
                        {})

                    # An OID can appear in multiple data sources/data points
                    oids.setdefault(oid, []).append(oidData)

        # return comp.getThresholdInstances('SNMP')
        return []


    def _createDeviceProxies(self, device):
        manage_ips = {device.manageIp: ([], False)}

        components = device.os.getMonitoredComponents(collector="zenperfsnmp")
        for component in components:
            manage_ip = get_component_manage_ip(component, device.manageIp)
            if manage_ip not in manage_ips:
                log.debug("Adding manage IP %s from %r" % (manage_ip, component))
                manage_ips[manage_ip] = ([], True)
            manage_ips[manage_ip][0].append(component)
        proxies = []
        for manage_ip, (components, components_only) in manage_ips.items():
            proxy = self._createDeviceProxy(device, manage_ip, components, components_only)
            if proxy is not None:
                proxies.append(proxy)
        return proxies

    def _createDeviceProxy(self, device, manage_ip=None, components=(), components_only=False):
        proxy = SnmpDeviceProxy()
        proxy = CollectorConfigService._createDeviceProxy(self, device, proxy)
        proxy.snmpConnInfo = SnmpConnInfo(device)
        if manage_ip is not None and manage_ip != device.manageIp:
            proxy._config_id = device.id + "_" + manage_ip
            proxy.snmpConnInfo.manageIp = manage_ip

        # framework expects a value for this attr but snmp task uses cycleInterval defined below
        proxy.configCycleInterval = getattr(device, 'zSnmpCollectionInterval', 300)
        # this is the attr zenperfsnmp actually uses
        proxy.cycleInterval = proxy.configCycleInterval

        proxy.name = device.id
        proxy.device = device.id
        proxy.lastmodeltime = device.getLastChangeString()
        proxy.lastChangeTime = float(device.getLastChange())

        # Gather the datapoints to retrieve
        proxy.oids = {}
        proxy.thresholds = []
        if not components_only:
            # First for the device....
            threshs = self._getComponentConfig(device, proxy.oids)
            if threshs:
                proxy.thresholds.extend(threshs)
        # And now for its components
        for comp in components:
            threshs = self._getComponentConfig(comp, proxy.oids)
            if threshs:
                proxy.thresholds.extend(threshs)

        if proxy.oids:
            return proxy


