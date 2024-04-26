##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function, absolute_import

import logging

from zope.component import createObject

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

from .cache import CacheQuery
from .dispatcher import BuildConfigTaskDispatcher
from .handlers import (
    NewDeviceHandler,
    DeviceUpdateHandler,
    MissingConfigsHandler,
)
from .utils import get_build_timeout, get_minimum_ttl, getConfigServices

log = logging.getLogger("zen.configcache")


class ConfigCache(object):
    """
    Implements an API for manipulating the Configuration Cache to the rest
    of the system.
    """

    @classmethod
    def new(cls):
        client = getRedisClient(url=getRedisUrl())
        store = createObject("configcache-store", client)
        configClasses = getConfigServices()
        dispatcher = BuildConfigTaskDispatcher(configClasses)
        return cls(store, dispatcher)

    def __init__(self, store, dispatcher):
        self.__new = NewDeviceHandler(log, store, dispatcher)
        self.__update = DeviceUpdateHandler(log, store, dispatcher)
        self.__missing = MissingConfigsHandler(log, store, dispatcher)
        self.__store = store

    def update(self, device):
        """
        Expires or retires existing configs for the device and sends build
        jobs to speculatively create new configurations for the device.
        May also delete configurations if a job produces no config for
        configuration that existed previously.
        """
        monitor = device.getPerformanceServerName()
        if monitor is None:
            raise RuntimeError(
                "Device '%s' is not a member of a collector" % (device.id,)
            )
        buildlimit = get_build_timeout(device)
        # Check for device class change
        stored_uid = self.__store.get_uid(device.id)
        if device.getPrimaryPath() != stored_uid:
            self.__new(device.id, monitor, buildlimit, False)
        else:
            # Note: the store's `search` method only returns keys for configs
            # that exist.
            keys_with_config = tuple(
                self.__store.search(
                    CacheQuery(monitor=monitor, device=device.id)
                )
            )
            minttl = get_minimum_ttl(device)
            self.__update(keys_with_config, minttl)
            self.__missing(device.id, monitor, keys_with_config, buildlimit)
