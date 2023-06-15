##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

# deviceconfig:<service-name>:<config-id> <pickled python data>
# ^            ^              ^
# |            |              +- The ID the config gives itself.
# |            +- Full name of the config class the produced the config
# +- Constant string that categorizes these values in Redis.

# deviceconfig:<service-name> [config-id-1, config-id-2, ...]

# Collector instances want a subset of configs from a config class.

# The config service will generate configurations and write the configs
# into Redis.  After generating all the configs, the list of config IDs
# is written to another key associated with the config class.
#
# The config service will expose a new API that returns the set of config IDs
# to the collector.  The API excepts the filter argument to distribute
# different sets of configs to different collector instances.  The collector
# uses the returned set of config IDs to read the configs from Redis.
#
# The 'maintenance cycle' of the collector includes getting a refreshed list
# of config IDs and updating its set of configs to match.  The collector will
# monitor Redis for changes in configs.

# The config service publishes updated config IDs to the
# "deviceconfignotify:<service-name>" channel.  The collector instances
# subscribe to this channel to become aware of which configs are stale and
# need to be refreshed from Redis.  In the collector, receiving updates
# from the pub/sub channel are used to mark stale configs. Prior to the next
# collection cycle, the collector will refresh the stale configs.

from __future__ import absolute_import, print_function

import ast
import logging

from collections import Container, Iterable, Sized

from twisted.spread.jelly import jelly, unjelly

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

_keybase = "deviceconfig"
_basepatterntemplate = "{}:{{}}:*".format(_keybase)
_basetemplate = "{}:{{}}:{{{{}}}}".format(_keybase)


log = logging.getLogger("zen.zenjobs")


def makeDeviceConfigurationStore(serviceId):
    """Create and return the DeviceConfigStore client."""
    client = getRedisClient(url=getRedisUrl())
    return DeviceConfigurationStore(client, serviceId)

# Type: DeviceProxy -> Products.ZenCollector.services.config.DeviceProxy


class DeviceConfigurationStore(Container, Iterable, Sized):
    """Implements an API for managing device configuration data.
    """

    def __init__(self, client, serviceid, expires=None):
        """Initialize a DeviceConfigurationStore instance.

        :param client: A Redis client instance.
        :type client: redis.StrictRedis
        :param serviceid: The full Python package name of the
            configuration service.
        :type serviceid: str
        :param expires: The number of seconds a key will exist.
        :type expires: Union[int, None]
        """
        self.__client = client
        self.__keypattern = _basepatterntemplate.format(serviceid)
        self.__keytemplate = _basetemplate.format(serviceid)
        self.__expires = expires

    def keys(self):
        """Return all existing config IDs.

        :rtype: Iterator[str]
        """
        return (
            key.split(":")[-1]
            for key in _iterkeys(self.__client, self.__keypattern)
        )

    def values(self):
        """Return all existing config data.

        :rtype: Iterator[DeviceProxy]
        """
        items = _iteritems(self.__client, self.__keypattern)
        return (_unjelly(data) for _, data in items)

    def items(self):
        """Return all existing config objects as (ID, config) pairs.

        :rtype: Iterator[Tuple[str, DeviceProxy]]]
        """
        items = _iteritems(self.__client, self.__keypattern)
        return ((key.split(":")[-1], _unjelly(data)) for key, data in items)

    def mget(self, *configids):
        """Return config data for each provided config ID.

        The returned iterable will produce the config data in the same
        order given in the configids parameter.

        :param configids: Iterable[str]
        :rtype: Iterator[DeviceProxy]
        """
        keys = (self.__keytemplate.format(configid) for configid in configids)
        raw = (
            self.__client.get(key) for key in keys if self.__client.exists(key)
        )
        return (_unjelly(data) for data in raw)

    def get(self, configid, default=None):
        """Return the config data for the given config ID.

        If the config ID is not found, the default argument is returned.

        :type configid: str
        :type default: Any
        :rtype: Union[DeviceProxy, default]
        """
        key = self.__keytemplate.format(configid)
        if not self.__client.exists(key):
            return default
        return _unjelly(self.__client.get(key))

    def __getitem__(self, configid):
        """Return the config object mapped by the given key.

        If the configuration ID is not found, a KeyError exception is raised.

        :type configid: str
        :rtype: DeviceProxy
        :raises: KeyError
        """
        key = self.__keytemplate.format(configid)
        if not self.__client.exists(key):
            raise KeyError("config not found: %s" % configid)
        return _unjelly(self.__client.get(key))

    def __setitem__(self, configid, data):
        """Insert or replace the config data for the given config ID.

        :type configid: str
        :param data: DeviceProxy
        :raises: ValueError
        """
        key = self.__keytemplate.format(configid)
        data = jelly(data)
        self.__client.set(key, data)

    def mdelete(self, *configids):
        """Delete the configs associated with each of the given config IDs.

        :param configids: An iterable producing config IDs
        :type configids: Iterable[str]
        """
        if not configids:
            return
        keys = (self.__keytemplate.format(configid) for configid in configids)
        self.__client.delete(*keys)

    def __delitem__(self, configid):
        """Delete the job data associated with the given job ID.

        If the job ID does not exist, a KeyError is raised.

        :type jobid: str
        """
        key = self.__keytemplate.format(configid)
        if not self.__client.exists(key):
            raise KeyError("Job not found: %s" % configid)
        self.__client.delete(key)

    def __contains__(self, configid):
        """Return True if job data exists for the given job ID.

        :type jobid: str
        :rtype: boolean
        """
        key = self.__keytemplate.format(configid)
        return self.__client.exists(key)

    def __len__(self):
        cursor = 0
        count = 0
        while True:
            cursor, keys = self.__client.scan(cursor, match=self.__keypattern)
            count += len(keys)
            if cursor == 0:
                break
        return count

    def __iter__(self):
        """Return an iterator producing all the config IDs in the datastore.

        :rtype: Iterator[str]
        """
        return self.keys()


def _iterkeys(client, keypattern):
    """Return an iterable of redis keys to config data."""
    cursor = 0
    while True:
        cursor, data = client.scan(cursor, match=keypattern)
        for key in data:
            yield key
        else:
            if cursor == 0:
                break


def _iteritems(client, keypattern):
    """Return an iterable of (redis key, config data) pairs.

    Only (key, data) pairs where data is not None are returned.
    """
    keys = _iterkeys(client, keypattern)
    raw = ((key, client.get(key)) for key in keys)
    return ((key, data) for key, data in raw if data)


def _unjelly(data):
    return unjelly(ast.literal_eval(data))
