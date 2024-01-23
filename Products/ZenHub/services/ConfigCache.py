##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from zope.component import createObject, getUtilitiesFor

from Products.ZenCollector.configcache.cache import ConfigQuery
from Products.ZenCollector.interfaces import IConfigurationDispatchingFilter
from Products.ZenHub.errors import translateError
from Products.ZenHub.HubService import HubService
from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl


class ConfigCache(HubService):
    """ZenHub service for retrieving device configs from Redis."""

    def __init__(self, dmd, monitor):
        """
        Initializes a ConfigCache instance.

        :param dmd: the Zenoss DMD reference
        :param monitor: the collector instance name
        """
        HubService.__init__(self, dmd, monitor)

        # Get the collector information (eg the 'localhost' collector)
        self._monitor = self.dmd.Monitors.Performance._getOb(self.instance)

        client = getRedisClient(url=getRedisUrl())
        self._store = createObject("configcache-store", client)

    @translateError
    def remote_getDeviceNames(self, servicename, options):
        """
        Return device IDs.

        @param servicename: Name of the configuration service.
        @type servicename: str
        @rtype: ImmutableSequence[str]
        """
        return tuple(
            key.device
            for key in self._filter(self._keys(servicename), options)
        )

    @translateError
    def remote_getDeviceConfigs(
        self, servicename, when, deviceids, options=None
    ):
        """
        Return a 'diff' of device configurations compared to `deviceids`.

        Device configurations that are new, updated, and removed relative
        to the `deviceids` argument are returned using a JSON structure that
        resembles the following:

            {
                "new": [DeviceProxy, ...],
                "updated": [DeviceProxy, ...],
                "removed": [str, ...]
            }

        The "new" entry will contain configurations for devices not found
        in `deviceids`.

        The "updated" entry will contain configurations that have changed
        since the `when` argument and are present in the `deviceids` argument.

        The "removed" entry will contain the IDs of devices found in
        `deviceids` but are not found in the cache or the caller is no longer
        responsible for those configurations.

        Device IDs appearing in `deviceids` but not included in the returned
        data should be considered as having unchanged configurations.

        @param servicename: Name of the configuration service.
        @type servicename: str
        @param when: When the last set of devices was returned.
        @type when: datetime.datetime
        @param names: Names of the devices to compare against.
        @type names: Sequence[str]
        @rtype: ImmutableSequence[DeviceProxy]
        """
        self.log.info(
            "[ConfigCache] getDeviceConfigs(%r, %r, %r, %r)",
            servicename,
            when,
            deviceids,
            options,
        )
        previous = set(deviceids)
        current_keys = tuple(self._filter(self._keys(servicename), options))

        # 'newest_keys' references devices not found in 'previous'
        newest_keys = (
            key for key in current_keys if key.device not in previous
        )

        # 'updated_keys' references newer configs found in 'previous'
        updated_keys = (
            key
            for key, _ in self._store.get_newer(
                when, service=servicename, monitor=self.instance
            )
            if key.device in previous
        )

        # 'removed' references devices found in 'previous'
        # but not in 'current'.
        current = set(key.device for key in current_keys)
        removed = previous - current

        return {
            "new": list(self._store.get(key).config for key in newest_keys),
            "updated": list(
                self._store.get(key).config for key in updated_keys
            ),
            "removed": list(removed),
        }

    def _keys(self, servicename):
        """
        Return all the device IDs associated with the current monitor and
        the given configuration service.

        @param servicename: Name of the configuration service.
        @type servicename: str
        @rtype: Iterator[str]
        """
        query = ConfigQuery(monitor=self.instance, service=servicename)
        self.log.info("[ConfigCache] using query %s", query)
        return self._store.search(query)

    def _filter(self, keys, options):
        """
        Returns a subset of device IDs in `names` based on the contents
        of the `options` parameter.

        @param keys: Cache config keys
        @type keys: Iterable[ConfigKey]
        @param options: Arguments into filters
        @type options: Mapping[str, Any]
        @rtype: Iterator[str]
        """
        # _filter is a generator function returning Device objects
        predicate = self._getOptionsFilter(options)
        for key in keys:
            try:
                if predicate(key.device):
                    yield key
            except Exception:
                if self.log.isEnabledFor(logging.DEBUG):
                    method = self.log.exception
                else:
                    method = self.log.warn
                method("error filtering device ID %s", key.device)

    def _getOptionsFilter(self, options):
        def _alwaysTrue(x):
            return True

        deviceFilter = _alwaysTrue
        if options:
            dispatchFilterName = (
                options.get("configDispatch", "") if options else ""
            )
            filterFactories = dict(
                getUtilitiesFor(IConfigurationDispatchingFilter)
            )
            filterFactory = filterFactories.get(
                dispatchFilterName, None
            ) or filterFactories.get("", None)
            if filterFactory:
                deviceFilter = filterFactory.getFilter(options) or deviceFilter
        return deviceFilter
