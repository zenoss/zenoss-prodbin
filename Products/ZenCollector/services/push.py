##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Acquisition import aq_parent
from twisted.internet import defer
from zope.component import getUtility

from Products.ZenHub.interfaces import IBatchNotifier
from Products.ZenHub.services.Procrastinator import Procrastinate
from Products.ZenHub.zodb import onUpdate, onDelete
from Products.ZenModel.Device import Device
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.PerformanceConf import PerformanceConf
from Products.ZenModel.privateobject import is_private
from Products.ZenModel.RRDTemplate import RRDTemplate
from Products.ZenModel.ZenPack import ZenPack
from Products.ZenUtils.AutoGCObjectReader import gc_cache_every
from Products.ZenUtils.picklezipper import Zipper

from .error import trapException
from .optionsfilter import getOptionsFilter


class UpdateCollectorMixin:
    """Push data back to collection daemons."""

    def __init__(self):
        # When about to notify daemons about device changes, wait for a little
        # bit to batch up operations.
        self._procrastinator = Procrastinate(self._pushConfig)
        self._reconfigProcrastinator = Procrastinate(self._pushReconfigure)

        self._notifier = getUtility(IBatchNotifier)

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

    def _notifyAll(self, device):
        """Notify all instances (daemons) of a change for the device."""
        # procrastinator schedules a call to _pushConfig
        self._procrastinator.doLater(device)

    def _pushConfig(self, device):
        """Push device config and deletes to relevent collectors/instances."""
        deferreds = []

        if self._perfIdFilter(device) and self._filterDevice(device):
            proxies = trapException(self, self._createDeviceProxies, device)
            if proxies:
                trapException(self, self._postCreateDeviceProxy, proxies)
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
                deviceFilter = getOptionsFilter(options)
                for proxy in proxies:
                    if deviceFilter(proxy):
                        deferreds.append(
                            self._sendDeviceProxy(listener, proxy)
                        )

        return defer.DeferredList(deferreds)

    def _sendDeviceProxy(self, listener, proxy):
        return listener.callRemote("updateDeviceConfig", proxy)

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
            deviceFilter = getOptionsFilter(options)
            filteredConfigs = filter(deviceFilter, configs)
            args = Zipper.dump(filteredConfigs)
            d = listener.callRemote("updateDeviceConfigs", args).addErrback(
                errback
            )
            deferreds.append(d)
        return deferreds


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
