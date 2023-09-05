##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import base64
import hashlib
import logging
import traceback

from Acquisition import aq_parent
from cryptography.fernet import Fernet
from twisted.internet import defer
from twisted.spread import pb
from ZODB.transact import transact
from zope import component

from Products.ZenEvents.ZenEventClasses import Critical
from Products.ZenHub.HubService import HubService
from Products.ZenHub.interfaces import IBatchNotifier
from Products.ZenHub.PBDaemon import translateError
from Products.ZenHub.services.Procrastinator import Procrastinate
from Products.ZenHub.services.ThresholdMixin import ThresholdMixin
from Products.ZenHub.zodb import onUpdate, onDelete
from Products.ZenModel.Device import Device
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.PerformanceConf import PerformanceConf
from Products.ZenModel.privateobject import is_private
from Products.ZenModel.RRDTemplate import RRDTemplate
from Products.ZenModel.ZenPack import ZenPack
from Products.ZenUtils.AutoGCObjectReader import gc_cache_every
from Products.ZenUtils.picklezipper import Zipper
from Products.Zuul.utils import safe_hasattr as hasattr

from ..interfaces import IConfigurationDispatchingFilter
from .metrics import measureConfigBuild


class DeviceProxy(pb.Copyable, pb.RemoteCopy):
    """Used to proxy device objects to collection services."""

    @property
    def configId(self):
        """
        This is the ID used by the framework to keep track of configurations,
        what to run, delete etc...

        Use this instead of `id` since certain daemons can use a
        configuration ID that is different than the underlying device ID.
        """
        cfgId = getattr(self, "_config_id", None)
        return cfgId if (cfgId is not None) else self.id

    @property
    def deviceGuid(self):
        return getattr(self, "_device_guid", None)

    def __str__(self):
        return self.id

    def __repr__(self):
        return "%s:%s" % (self.__class__.__name__, self.id)


pb.setUnjellyableForClass(DeviceProxy, DeviceProxy)


# Default attributes copied to every device proxy.
BASE_ATTRIBUTES = (
    "id",
    "manageIp",
)


class CollectorConfigService(HubService, ThresholdMixin):
    """Base class for ZenHub configuration service classes."""

    def __init__(self, dmd, instance, deviceProxyAttributes=()):
        """
        Initializes a CollectorConfigService instance.

        @param dmd: the Zenoss DMD reference
        @param instance: the collector instance name
        @param deviceProxyAttributes: a tuple of names for device attributes
            that should be copied to every device proxy created
        @type deviceProxyAttributes: tuple
        """
        HubService.__init__(self, dmd, instance)

        self._deviceProxyAttributes = BASE_ATTRIBUTES + deviceProxyAttributes

        # Get the collector information (eg the 'localhost' collector)
        self._prefs = self.dmd.Monitors.Performance._getOb(self.instance)
        self.config = self._prefs  # Needed for ThresholdMixin
        self.configFilter = None

        # When about to notify daemons about device changes, wait for a little
        # bit to batch up operations.
        self._procrastinator = Procrastinate(self._pushConfig)
        self._reconfigProcrastinator = Procrastinate(self._pushReconfigure)

        self._notifier = component.getUtility(IBatchNotifier)

    def _wrapFunction(self, functor, *args, **kwargs):
        """
        Call the functor using the arguments,
        and trap any unhandled exceptions.

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
        except Exception as ex:
            msg = "Unhandled exception in zenhub service %s: %s" % (
                self.__class__,
                ex,
            )
            self.log.exception(msg)
            self.sendEvent(
                dict(
                    severity=Critical,
                    component=str(self.__class__),
                    traceback=traceback.format_exc(),
                    summary=msg,
                    device=self.instance,
                    methodCall="%s(%s, %s)" % (functor.__name__, args, kwargs),
                )
            )

    @onUpdate(PerformanceConf)
    def perfConfUpdated(self, conf, event):
        with gc_cache_every(1000, db=self.dmd._p_jar._db):
            if conf.id == self.instance:
                for listener in self.listeners:
                    listener.callRemote(
                        "setPropertyItems", conf.propertyItems()
                    )

    @onUpdate(ZenPack)
    def zenPackUpdated(self, zenpack, event):
        with gc_cache_every(1000, db=self.dmd._p_jar._db):
            for listener in self.listeners:
                try:
                    listener.callRemote(
                        "updateThresholdClasses",
                        self.remote_getThresholdClasses(),
                    )
                except Exception:
                    self.log.warning(
                        "Error notifying a listener of new classes"
                    )

    @onUpdate(Device)
    def deviceUpdated(self, device, event):
        with gc_cache_every(1000, db=self.dmd._p_jar._db):
            self._notifyAll(device)

    @onUpdate(None)  # Matches all
    def notifyAffectedDevices(self, entity, event):
        # FIXME: This is horrible
        with gc_cache_every(1000, db=self.dmd._p_jar._db):
            if isinstance(entity, self._getNotifiableClasses()):
                self._reconfigureIfNotify(entity)
            else:
                if isinstance(entity, Device):
                    return
                # Something else... mark the devices as out-of-date
                template = None
                while entity:
                    # Don't bother with privately managed objects; the ZenPack
                    # will handle them on its own
                    if is_private(entity):
                        return
                    # Walk up until you hit an organizer or a device
                    if isinstance(entity, RRDTemplate):
                        template = entity
                    if isinstance(entity, DeviceClass):
                        uid = (self.name(), self.instance)
                        devfilter = None
                        if template:
                            devfilter = _HasTemplate(template, self.log)
                        self._notifier.notify_subdevices(
                            entity, uid, self._notifyAll, devfilter
                        )
                        break
                    if isinstance(entity, Device):
                        self._notifyAll(entity)
                        break
                    entity = aq_parent(entity)

    @onDelete(Device)
    def deviceDeleted(self, device, event):
        with gc_cache_every(1000, db=self.dmd._p_jar._db):
            devid = device.id
            collector = device.getPerformanceServer().getId()
            # The invalidation is only sent to the collector where the
            # deleted device was.
            if collector == self.instance:
                self.log.debug(
                    "Invalidation: Performing remote call to delete "
                    "device %s from collector %s",
                    devid,
                    self.instance,
                )
                for listener in self.listeners:
                    listener.callRemote("deleteDevice", devid)
            else:
                self.log.debug(
                    "Invalidation: Skipping remote call to delete "
                    "device %s from collector %s",
                    devid,
                    self.instance,
                )

    @translateError
    def remote_getConfigProperties(self):
        return self._prefs.propertyItems()

    @translateError
    def remote_getDeviceNames(self, options=None):
        devices = self._getDevices(
            deviceFilter=self._getOptionsFilter(options)
        )
        return [x.id for x in self._filterDevices(devices)]

    def _getDevices(self, deviceNames=None, deviceFilter=None):

        if not deviceNames:
            devices = filter(deviceFilter, self._prefs.devices())
        else:
            devices = []
            for name in deviceNames:
                device = self.dmd.Devices.findDeviceByIdExact(name)
                if not device:
                    continue
                else:
                    if deviceFilter(device):
                        devices.append(device)
        return devices

    @translateError
    def remote_getDeviceConfigs(self, deviceNames=None, options=None):
        deviceFilter = self._getOptionsFilter(options)
        devices = self._getDevices(deviceNames, deviceFilter)
        devices = self._filterDevices(devices)

        deviceConfigs = []
        for device in devices:
            proxies = self._wrapFunction(self._createDeviceProxies, device)
            if proxies:
                deviceConfigs.extend(proxies)

        self._wrapFunction(self._postCreateDeviceProxy, deviceConfigs)
        return deviceConfigs

    @transact
    def _create_encryption_key(self):
        # Double-check to make sure somebody else hasn't created it
        collector = self.getPerformanceMonitor()
        key = getattr(collector, "_encryption_key", None)
        if key is None:
            key = collector._encryption_key = Fernet.generate_key()
        return key

    @translateError
    def remote_getEncryptionKey(self):
        # Get or create an encryption key for this collector
        key = getattr(
            self.getPerformanceMonitor(),
            "_encryption_key",
            self._create_encryption_key(),
        )

        # Hash the key with the daemon identifier to get unique key
        # per collector daemon.
        s = hashlib.sha256()
        s.update(key)
        s.update(self.name())
        return base64.urlsafe_b64encode(s.digest())

    def _postCreateDeviceProxy(self, deviceConfigs):
        pass

    def _createDeviceProxies(self, device):
        proxy = self._createDeviceProxy(device)
        return (proxy,) if (proxy is not None) else ()

    def _createDeviceProxy(self, device, proxy=None):
        """
        Creates a device proxy object that may be copied across the network.

        Subclasses should override this method, call it for a basic DeviceProxy
        instance, and then add any additional data to the proxy as their needs
        require.

        @param device: the regular device object to create a proxy from
        @return: a new device proxy object, or None if no proxy can be created
        @rtype: DeviceProxy
        """
        proxy = proxy if (proxy is not None) else DeviceProxy()

        # copy over all the attributes requested
        for attrName in self._deviceProxyAttributes:
            setattr(proxy, attrName, getattr(device, attrName, None))

        if isinstance(device, Device):
            from Products.ZenUtils.guid.interfaces import IGlobalIdentifier

            guid = IGlobalIdentifier(device).getGUID()
            if guid:
                setattr(proxy, "_device_guid", guid)
        return proxy

    def _filterDevice(self, device):
        """
        Determines if the specified device should be included for consideration
        in being sent to the remote collector client.

        Subclasses should override this method, call it for the default
        filtering behavior, and then add any additional filtering as needed.

        @param device: the device object to filter
        @return: True if this device should be included for further processing
        @rtype: boolean
        """
        try:
            return device.monitorDevice() and (
                not self.configFilter or self.configFilter(device)
            )
        except AttributeError as e:
            self.log.warn(
                "got an attribute exception on device.monitorDevice()"
            )
            self.log.debug(e)
        return False

    def _getOptionsFilter(self, options):
        def _alwaysTrue(x):
            return True

        deviceFilter = _alwaysTrue
        if options:
            dispatchFilterName = (
                options.get("configDispatch", "") if options else ""
            )
            filterFactories = dict(
                component.getUtilitiesFor(IConfigurationDispatchingFilter)
            )
            filterFactory = filterFactories.get(
                dispatchFilterName, None
            ) or filterFactories.get("", None)
            if filterFactory:
                deviceFilter = filterFactory.getFilter(options) or deviceFilter
        return deviceFilter

    def _filterDevices(self, devices):
        """
        Filters out devices from the provided list that should not be
        converted into DeviceProxy instances and sent back to the collector
        client.

        @param device: the device object to filter
        @return: a list of devices that are to be included
        @rtype: list
        """
        filteredDevices = []
        for dev in (d for d in devices if d is not None):
            try:
                device = dev.primaryAq()
                if self._perfIdFilter(device) and self._filterDevice(device):
                    filteredDevices.append(device)
                    self.log.debug("Device %s included by filter", device.id)
                else:
                    # don't use .id just in case something crazy returned.
                    self.log.debug("Device %r excluded by filter", device)
            except Exception:
                if self.log.isEnabledFor(logging.DEBUG):
                    self.log.exception("Got an exception filtering %r", dev)
                else:
                    self.log.warn("Got an exception filtering %r", dev)
        return filteredDevices

    def _perfIdFilter(self, obj):
        """
        Return True if obj is not a device (has no perfServer attribute)
        or if the device's associated monitor has a name matching this
        collector's name.  Otherise, return False.
        """
        return (
            not hasattr(obj, "perfServer")
            or obj.perfServer.getRelatedId() == self.instance
        )

    def _notifyAll(self, device):
        """Notify all instances (daemons) of a change for the device."""
        # procrastinator schedules a call to _pushConfig
        self._procrastinator.doLater(device)

    def _pushConfig(self, device):
        """Push device config and deletes to relevent collectors/instances."""
        deferreds = []

        if self._perfIdFilter(device) and self._filterDevice(device):
            with measureConfigBuild(self, device):
                proxies = self._wrapFunction(self._createDeviceProxies, device)
                if proxies:
                    self._wrapFunction(self._postCreateDeviceProxy, proxies)
        else:
            proxies = None

        prev_collector = (
            device.dmd.Monitors.primaryAq().getPreviousCollectorForDevice(
                device.id
            )
        )
        for listener in self.listeners:
            if not proxies:
                if hasattr(device, "getPerformanceServer"):
                    # The invalidation is only sent to the previous and
                    # current collectors.
                    if self.instance in (
                        prev_collector,
                        device.getPerformanceServer().getId(),
                    ):
                        self.log.debug(
                            "Invalidation: Performing remote call for "
                            "device %s on collector %s",
                            device.id,
                            self.instance,
                        )
                        deferreds.append(
                            listener.callRemote("deleteDevice", device.id)
                        )
                    else:
                        self.log.debug(
                            "Invalidation: Skipping remote call for "
                            "device %s on collector %s",
                            device.id,
                            self.instance,
                        )
                else:
                    deferreds.append(
                        listener.callRemote("deleteDevice", device.id)
                    )
                    self.log.debug(
                        "Invalidation: Performing remote call for "
                        "device %s on collector %s",
                        device.id,
                        self.instance,
                    )
            else:
                options = self.listenerOptions.get(listener, None)
                deviceFilter = self._getOptionsFilter(options)
                for proxy in proxies:
                    if deviceFilter(proxy):
                        deferreds.append(
                            self._sendDeviceProxy(listener, proxy)
                        )

        return defer.DeferredList(deferreds)

    def _sendDeviceProxy(self, listener, proxy):
        return listener.callRemote("updateDeviceConfig", proxy)

    def sendDeviceConfigs(self, configs):
        deferreds = []

        def errback(failure):
            self.log.critical(
                "Unable to update configs for service instance %s: %s",
                self.name(),
                failure,
            )

        for listener in self.listeners:
            options = self.listenerOptions.get(listener, None)
            deviceFilter = self._getOptionsFilter(options)
            filteredConfigs = filter(deviceFilter, configs)
            args = Zipper.dump(filteredConfigs)
            d = listener.callRemote("updateDeviceConfigs", args).addErrback(
                errback
            )
            deferreds.append(d)
        return deferreds

    # FIXME: Don't use _getNotifiableClasses, use @onUpdate(myclasses)
    def _getNotifiableClasses(self):
        """
        Return a tuple of classes.

        When any object of a type in the sequence is modified the collector
        connected to the service will be notified to update its configuration.

        @rtype: tuple
        """
        return ()

    def _pushReconfigure(self, value):
        """Notify the collector to reread the entire configuration."""
        # value is unused but needed for the procrastinator framework
        for listener in self.listeners:
            listener.callRemote("notifyConfigChanged")
        self._reconfigProcrastinator.clear()

    def _reconfigureIfNotify(self, object):
        ncc = self._notifyConfigChange(object)
        self.log.debug(
            "services/config.py _reconfigureIfNotify object=%r "
            "_notifyConfigChange=%s",
            object,
            ncc,
        )
        if ncc:
            self.log.debug("scheduling collector reconfigure")
            self._reconfigProcrastinator.doLater(True)

    def _notifyConfigChange(self, object):
        """
        Called when an object of a type from _getNotifiableClasses is
        encountered

        @return: should a notify config changed be sent
        @rtype: boolean
        """
        return True


class _HasTemplate(object):
    """
    Predicate class that checks whether a given device has a template
    matching the given template.
    """

    def __init__(self, template, log):
        self.template = template
        self.log = log

    def __call__(self, device):
        if issubclass(self.template.getTargetPythonClass(), Device):
            if self.template in device.getRRDTemplates():
                self.log.debug(
                    "%s bound to template %s",
                    device.getPrimaryId(),
                    self.template.getPrimaryId(),
                )
                return True
            else:
                self.log.debug(
                    "%s not bound to template %s",
                    device.getPrimaryId(),
                    self.template.getPrimaryId(),
                )
                return False
        else:
            # check components, Too expensive?
            for comp in device.getMonitoredComponents(
                type=self.template.getTargetPythonClass().meta_type
            ):
                if self.template in comp.getRRDTemplates():
                    self.log.debug(
                        "%s bound to template %s",
                        comp.getPrimaryId(),
                        self.template.getPrimaryId(),
                    )
                    return True
                else:
                    self.log.debug(
                        "%s not bound to template %s",
                        comp.getPrimaryId(),
                        self.template.getPrimaryId(),
                    )
            return False


class NullConfigService(CollectorConfigService):
    """
    The collector framework requires a configuration service, but some
    daemons do not need any configuration.
    """

    def __init__(self, dmd, instance):
        CollectorConfigService.__init__(self, dmd, instance)

    def _filterDevices(self, deviceList):
        return []
