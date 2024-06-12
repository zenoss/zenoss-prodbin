##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function, absolute_import

import time

from .cache import CacheKey, CacheQuery, ConfigStatus


class NewDeviceHandler(object):

    def __init__(self, log, store, dispatcher):
        self.log = log
        self.store = store
        self.dispatcher = dispatcher

    def __call__(self, deviceId, monitor, buildlimit, newDevice=True):
        all_keys = set(
            CacheKey(svcname, monitor, deviceId)
            for svcname in self.dispatcher.service_names
        )
        query = CacheQuery(device=deviceId, monitor=monitor)
        pending_keys = set(
            status.key
            for status in self.store.query_statuses(query)
            if isinstance(status, ConfigStatus.Pending)
        )
        non_pending_keys = all_keys - pending_keys
        for key in pending_keys:
            self.log.info(
                "build job already submitted for this config  "
                "device=%s collector=%s service=%s",
                key.device,
                key.monitor,
                key.service,
            )
        now = time.time()
        self.store.set_pending(
            *((key, now) for key in non_pending_keys)
        )
        for key in non_pending_keys:
            self.dispatcher.dispatch(
                key.service, key.monitor, key.device, buildlimit, now
            )
            self.log.info(
                "submitted build job for %s  "
                "device=%s collector=%s service=%s",
                "new device" if newDevice else "device with new device class",
                key.device,
                key.monitor,
                key.service,
            )


class DeviceUpdateHandler(object):

    def __init__(self, log, store, dispatcher):
        self.log = log
        self.store = store
        self.dispatcher = dispatcher

    def __call__(self, keys, minttl):
        current_statuses = tuple(
            status
            for key in keys
            for status in self.store.get_status(key)
            if isinstance(status, ConfigStatus.Current)
        )

        now = time.time()
        retirement = now - minttl

        retired = set(
            status.key
            for status in current_statuses
            if status.updated >= retirement
        )
        expired = set(
            status.key
            for status in current_statuses
            if status.key not in retired
        )

        self.store.set_retired(*((key, now) for key in retired))
        self.store.set_expired(*((key, now) for key in expired))

        for key in retired:
            self.log.info(
                "retired configuration of changed device  "
                "device=%s collector=%s service=%s",
                key.device,
                key.monitor,
                key.service,
            )
        for key in expired:
            self.log.info(
                "expired configuration of changed device  "
                "device=%s collector=%s service=%s",
                key.device,
                key.monitor,
                key.service,
            )


class MissingConfigsHandler(object):

    def __init__(self, log, store, dispatcher):
        self.log = log
        self.store = store
        self.dispatcher = dispatcher

    def __call__(self, deviceId, monitor, keys, buildlimit):
        """
        @param keys: These keys are associated with a config
        @type keys: Sequence[CacheKey]
        """
        # Send a job for for all config services that don't currently have
        # an associated configuration.  Some ZenPacks, i.e. vSphere, defer
        # their modeling to a later time, so jobs for configuration services
        # must be sent to pick up any new configs.
        hasconfigs = tuple(key.service for key in keys)
        noconfigkeys = tuple(
            CacheKey(svcname, monitor, deviceId)
            for svcname in self.dispatcher.service_names
            if svcname not in hasconfigs
        )
        # Identify all no-config keys that already have a status.
        skipkeys = tuple(
            status.key
            for key in noconfigkeys
            for status in self.store.get_status(key)
            if status is not None
        )
        now = time.time()
        for key in (k for k in noconfigkeys if k not in skipkeys):
            self.store.set_pending((key, now))
            self.dispatcher.dispatch(
                key.service, key.monitor, key.device, buildlimit, now
            )
            self.log.debug(
                "submitted build job for possibly missing config  "
                "device=%s collector=%s service=%s",
                key.device,
                key.monitor,
                key.service,
            )


class RemoveConfigsHandler(object):

    def __init__(self, log, store):
        self.log = log
        self.store = store

    def __call__(self, keys):
        self.store.remove(*keys)
        for key in keys:
            self.log.info(
                "removed configuration of deleted device  "
                "device=%s collector=%s service=%s",
                key.device,
                key.monitor,
                key.service,
            )
