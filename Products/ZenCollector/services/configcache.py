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

from cryptography.fernet import Fernet

# from twisted.internet import defer
from ZODB.transact import transact
from zope.component import getUtilitiesFor

from Products.ZenHub.HubService import HubService
from Products.ZenHub.PBDaemon import translateError
from Products.ZenHub.modelchange.configstore import (
    makeDeviceConfigurationStore,
    makeMonitorDeviceMappingStore,
)
from Products.ZenModel.Device import Device
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.Zuul.utils import safe_hasattr as hasattr

from ..interfaces import IConfigurationDispatchingFilter


class DeviceConfigCache(HubService):
    """ZenHub service for retrieving device configs from Redis."""

    def __init__(self, dmd, instance):
        """
        Initializes a DeviceConfigCache instance.

        :param dmd: the Zenoss DMD reference
        :param instance: the collector instance name
        """
        HubService.__init__(self, dmd, instance)

        # Get the collector information (eg the 'localhost' collector)
        self._monitor = self.dmd.Monitors.Performance._getOb(self.instance)

        self._redis = None  # Redis client
        self._configStores = {}  # device config stores keyed by service name
        self._monitorStore = makeMonitorDeviceMappingStore(self.instance)

    @translateError
    def remote_getConfigProperties(self):
        return self._monitor.propertyItems()

    @translateError
    def remote_getDeviceNames(self, serviceId, options):
        store = self._getStore(serviceId)
        return [devId for devId in self._select(store.keys(), options)]

    @translateError
    def remote_getCachedDeviceConfigs(
        self, serviceId, names=None, options=None
    ):
        store = self._getStore(serviceId)
        if not names:
            names = iter(self._monitorStore)
        selected = self._select(names, options)
        return list(store.mget(*selected))

    def _getStore(self, serviceid):
        if serviceid not in self._configStores:
            self._configStores[serviceid] = makeDeviceConfigurationStore(
                serviceid
            )
        return self._configStores[serviceid]

    def _select(self, names, options):
        # _select is a generator function returning Device objects
        # `devices` is an iterator returning strings.
        # `options` is a dict-like
        predicate = self._getOptionsFilter(options)
        for devId in names:
            try:
                if all(
                    (
                        predicate(devId),
                        self._monitorFilter(devId),
                    )
                ):
                    yield devId
            except Exception:
                if self.log.isEnabledFor(logging.DEBUG):
                    method = self.log.exception
                else:
                    method = self.log.warn
                method("error filtering device ID %s", devId)

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

    def _getOptionsFilter(self, options):
        if options:
            name = options.get("configDispatch", "") if options else ""
            factories = dict(getUtilitiesFor(IConfigurationDispatchingFilter))
            factory = factories.get(name, None)
            if factory is None:
                factory = factories.get("", None)
            if factory is not None:
                devicefilter = factory.getFilter(options)
                if devicefilter:
                    return devicefilter

        return lambda x: True

    def _monitorFilter(self, obj):
        """
        Return True if the device is monitored by the same collector the
        requesting collection daemon is a member of.
        """
        # Probably need to store this data in Redis:
        # - In the key? Then keys become hashes
        # - In a separate key?  Use a set to store a bunch device IDs.
        #   A different set for each monitor/collector.
        return True
        # return (
        #     not hasattr(obj, "perfServer")
        #     or obj.perfServer.getRelatedId() == self.instance
        # )
