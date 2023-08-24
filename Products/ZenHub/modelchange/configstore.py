##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

# Key structure
# zenconfig:device:<service-name>:<config-id> <pickled python data>
# ^         ^      ^              ^
# |         |      |              +- The ID the config gives itself.
# |         |      +- Full name of the config class the produced the config
# |         +- Category
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

# Usage Patterns
# ==============
#
# Attributes
# ----------
# - 'service' is the name of the service.  This value never changes.
# - 'monitor' is the name of the monitor/collector.  This value will
#   change when a device is moved between collectors.
# - 'last-update' is a Unix timestamp of the last update to the configuration.
#   This value will change every time the configuration is changed.
#
# Cases
# -----
# 1. Get configuration IDs according to service, monitor, and last-update.
#    The 'last-update' is used to select config IDs of configs that
#    have changed since the 'last-update' value.
#
#    Config IDs in stored in a sorted set.  The key is formed using the
#    service and monitor names. The last-update values are the scores
#    associated with each config ID in the set.
#
# 2. Get the configurations for the given configuration IDs
# 3. Write a new configuration
# 4. Move a device from one monitor to another
# 5. Device is deleted

from __future__ import absolute_import, print_function

import ast
import logging

from collections import Container, Sized
from itertools import chain, islice

from twisted.spread.jelly import jelly, unjelly

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

_app = "zenconfig"
_basepatterntemplate = "{}:{{}}:{{}}:{{}}:*".format(_app)
_basetemplate = "{}:{{}}:{{}}:{{}}:{{{{}}}}".format(_app)

log = logging.getLogger("zen.zenjobs")


class DeviceConfigurationKey(object):
    """
    The key to a specific configuration.
    """

    __slots__ = ("service", "configid")

    def __init__(self, service, configid):
        self.service = service
        self.configid = configid

    def __str__(self):
        return "{}:device:config:{}:{}".format(
            _app, self.service, self.configid
        )


class ConfigurationRecord(object):

    __slots__ = ("key", "data")


def makeDeviceConfigurationStore():
    """
    Create and return a ConfigurationStore for device configurations.

    :param serviceid: The full Python package name of the
        configuration service.
    :type serviceid: str
    """
    client = getRedisClient(url=getRedisUrl())
    segments = ("service", "device")
    return ConfigurationStore(client, segments)

# cfg:device:service:<service-name>:<config-id> <config-data>
# cfg:device:monitor:<monitor-name>:<service-name> <(time, config-id), ...>
#
# How to track when a device is moved from one monitor to another?
# - How to notify collection daemons of this activity?
#   - The receiving daemon is notified because it'll show up when updates
#     are requested.
#   - Where can the losing daemon look to determine it's no longer
#     responsible for a device?
#     - Maybe a flag to indicate that the collection daemon needs to
#       refresh (sync?) its set of device configs?  A "refresh" meaning
#       it verifies that its local cache matches the data in Redis.
# - How to track when a device is deleted?
#   - A flag is set that the losing daemon will notice?
#     - The data is organized by monitor and service, not specific daemons.
#       I don't want to cause all daemons to refresh their local caches.
# - Use a notification pubsub channel? -- still need to know specific
#   daemon instances so that messages are sent to the correct place.
#
# Redis is fast, so maybe always load the cfg:device:monitor:*:* key and
# compare that set against the local cache?  Remove configs from the local
# cache that aren't present in the set and request newer configs, comparing
# the timestamps locally rather than using zrangebyscore.  This may sidestep
# the load on Redis that zrangebyscore could cause if the key has a enough
# members in the set, although a large enough set to cause this issue may
# cause issues with reading the key on the Python side.


class ConfigurationStore(Container, Sized):
    """Implements an API for managing configuration data."""

    def __init__(self, client, keysegments, expires=None, batchsize=100):
        """Initialize a ConfigurationStore instance.

        :param client: A Redis client instance.
        :type client: redis.StrictRedis
        :param keysegments: A list of names used to identify values.
        :type keysegments: Sequence[str]
        :param expires: The number of seconds a key will exist.
        :type expires: Union[int, None]
        :param batchsize: The number of key values to retrieve at a time
            for certain APIs.  The default size is 100.
        :type batchsize: int
        """
        self.__client = client
        self.__configkeytemplate = (
            "{app}:{segments}:{{service}}:{{configid}}".format(
                app=_app, segments=":".join(keysegments)
            )
        )
        self.__keypattern = "{app}:device:config:*".format(app=_app)
        self.__expires = expires
        self.__batchsize = batchsize

    def _makekey(self, service, configid):
        return self.__keytemplate.format(service=service, configid=configid)

    def __contains__(self, key):
        """Return True if configuration data exists for the given record.

        :type key: DeviceConfigurationKey
        :rtype: boolean
        """
        return self.__client.exists(key)

    def __len__(self):
        return sum(1 for _ in self.__client.scan_iter(match=self.__keypattern))

    def _keyiter(self, service=None, monitor=None):
        if monitor is not None:
            key = "{}:device:monitor:{}".format(_app, monitor)
            if service is not None:
                pattern = "{}:*".format(service)
                return (
                    elem[0]
                    for elem in self.__client.zscan_iter(key, match=pattern)
                )
            else:
                return (elem[0] for elem in self.__client.zscan_iter(key))

        if service is not None:
            pattern = self.__keytemplate.format(service=service, configid="*")
        else:
            pattern = self.__keypattern
        return self.__client.scan_iter(match=pattern)

    def keys(self, service=None, monitor=None):
        """Return the keys matching search criteria.

        :rtype: Iterator[DeviceConfigurationKey]
        """
        keys = self._keyiter(service, monitor)
        return (DeviceConfigurationKey(*key.split(":")[-2:]) for key in keys)

    def values(self, service=None, monitor=None):
        """Return the ConfigurationRecords matching the search criteria.

        :rtype: Iterator[ConfigurationRecord]
        """
        # generator to build the config keys
        keys = (
            "{}:device:config:{}".format(_app, *k.split(":")[-2:])
            for k in self._keyiter(service, monitor)
        )
        raw = ((key, self.__client.get(key)) for key in keys)
        return (ConfigurationRecord(key, data) for key, data in raw if data)

    def items(self, service=None, monitor=None):
        """Return all existing config objects as (ID, config) pairs.

        :rtype: Iterator[Tuple[str, IJellyable]]]
        """
        keys = (
            "{}:device:config:{}".format(_app, *k.split(":")[-2:])
            for k in self._keyiter(service, monitor)
        )
        raw = ((key, self.__client.get(key)) for key in keys)
        return (
            (DeviceConfigurationKey(key), ConfigurationRecord(key, data))
            for key, data in raw if data
        )

    def mget(self, configids):
        """Return config data for each provided config ID.

        The returned iterable will produce the config data in the same
        order given in the configids parameter.

        :param configids: Iterable[str]
        :rtype: Iterator[IJellyable]
        """
        keys = (self.__keytemplate.format(cid) for cid in configids)
        raw = (
            self.__client.mget(batch)
            for batch in _batched(keys, self._batchsize)
        )
        return (_unjelly(data) for data in chain.from_iterable(raw))

    def get(self, configid, default=None):
        """Return the config data for the given config ID.

        If the config ID is not found, the default argument is returned.

        :type configid: str
        :type default: Any
        :rtype: Union[IJellyable, default]
        """
        key = self.__keytemplate.format(configid)
        if not self.__client.exists(key):
            return default
        return _unjelly(self.__client.get(key))

    def __getitem__(self, configid):
        """Return the config object mapped by the given key.

        If the configuration ID is not found, a KeyError exception is raised.

        :type configid: str
        :rtype: IJellyable
        :raises: KeyError
        """
        key = self.__keytemplate.format(configid)
        if not self.__client.exists(key):
            raise KeyError("config not found: %s" % configid)
        return _unjelly(self.__client.get(key))

    def __setitem__(self, configid, data):
        """Insert or replace the config data for the given config ID.

        :type configid: str
        :param data: IJellyable
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


def _iteritems(client, keypattern):
    """Return an iterable of (redis key, config data) pairs.

    Only (key, data) pairs where data is not None are returned.
    """
    keys = client.scan_iter(match=keypattern)
    raw = ((key, client.get(key)) for key in keys)
    return ((key, data) for key, data in raw if data)


def _unjelly(data):
    return unjelly(ast.literal_eval(data))


def _batched(iterable, n):
    """
    Batch data into tuples of length `n`.  The last batch may be shorter.

    >>> list(batched('ABCDEFG', 3))
    [('A', 'B', 'C'), ('D', 'E', 'F'), ('G',)]
    """
    if n < 1:
        raise ValueError("n must be greater than zero")
    itr = iter(iterable)
    while True:
        batch = tuple(islice(itr, n))
        if not batch:
            break
        yield batch
    #
    # Note: In Python 3.7+, the above loop would be
    #     while (batch := tuple(islice(it, n))):
    #         yield batch
