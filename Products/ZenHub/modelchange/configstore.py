##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

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
# Use Cases
# ---------
# 1. Return configuration IDs having 'last-update' timestamps greater than
#    a given timestamp.
#
#    Config IDs in stored in a sorted set.  The key is formed using the
#    service and monitor names. The last-update values are the scores
#    associated with each config ID in the set.
#
# 2. Return all configurations newer than a given timestamp.
#
# 3. Return the configurations for a given set of devices (1+).
#    a. Client will request configurations for a set of devices.
#
# 4. Create the configuration for new devices.
#
# 5. Refresh configurations that exceed some age.
#
# 6. Update a configuration's metadata when a device is moved between monitors.
#    a. Client will request updates for a given set of devices; devices not
#       assigned to the current monitor will be marked 'not found' in the
#       response.
#
# 7. Remove a configuration when a device is deleted.
#    a. Client will request updates for a given set of devices; devices that
#       aren't found will be marked 'not found' in the response.

# When requesting updates, the client will provide the set of devices it
# knows, with a timestamp associated with each device.
# The server will respond with configs that have newer timestamps than what
# the client provided.  If a device is no longer available for the client,
# a 'not found' marker is returned instead of a config.
# The server will also respond with configs for devices that were not given
# by the client, but are available to the client.

# Key structure
# =============
# modelchange:device:config:<monitor>:<service>:<id> <data>
# modelchange:device:age:<monitor>:<service> <data>
#
# While "device" seems redundant, other values in this position could be
# "threshold" and "property".
#
# The "config" segment identifies a key storing a device configuration.
# The "age" segment identifies a key storing a set of device IDs sorted by
# the timestamp of when the configuration was created.
#
# <monitor> names the monitor (collector) the device belongs to.
# <service> names the configuration service class used to generate the
# configuration.
#
# <id> is the ID of the device
#

from __future__ import absolute_import, print_function, division

import ast
import logging
import time

from itertools import chain, islice

from twisted.spread.jelly import jelly, unjelly

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

_app = "modelchange"
log = logging.getLogger("zen.modelchange")


class DeviceConfigStore(object):
    """
    Manages device configuration data for a specific configuration service.
    """

    @classmethod
    def make(cls, servicename):
        """
        Create and return a DeviceConfigStore for device configurations.

        The `servicename` parameter should be the fully qualified module name
        to the class used to generate the device configurations.

        :param servicename: The name of the device config class
        :type servicename: str
        """
        client = getRedisClient(url=getRedisUrl())
        return cls(client, servicename)

    def __init__(self, client, service):
        """Initialize a ConfigurationStore instance.

        :param client: A Redis client instance.
        :type client: redis.StrictRedis
        :param service: The name of the configuration service.
        :type service: str
        :param batchsize: The number of key values to retrieve at a time
            for certain APIs.  The default size is 100.
        :type batchsize: int
        """
        self.__client = client
        # modelchange:device:config:<monitor>:<service>:<id> <data>
        self.__template = (
            "{app}:device:config:{{monitor}}:{service}:{{device}}".format(
                app=_app, service=service
            )
        )
        self.__scan_count = 1000
        self.__mget_count = 10

    def _makekey(self, monitorid, configid):
        return self.__template.format(monitor=monitorid, device=configid)

    def exists(self, monitorid, configid):
        """Return True if configuration data exists for the given ID.

        :param monitorid: Name of the monitor the device is a member of.
        :type monitorid: str
        :param configid: The ID of the device
        :type configid: str
        :rtype: boolean
        """
        return self.__client.exists(self._makekey(monitorid, configid))

    def search(self, monitorid="*", configid="*"):
        """
        Return an iterable of tuples of (monitorid, configId).
        """
        pattern = self._makekey(monitorid, configid)
        return (
            (key.split(":")[3], key.split(":")[-1])
            for key in self.__client.scan_iter(
                match=pattern, count=self.__scan_count
            )
        )

    def mget(self, *configids):
        """Return config data for each provided monitor ID/config ID pair.

        The returned iterable will produce the config data in the same
        order given in the configids parameter.

        The returned iterable is empty if none of the given config IDs exist.

        :param configids: Iterable[(str, str)]
        :rtype: Iterator[IJellyable]
        """
        keys = (self._makekey(*cid) for cid in configids)
        raw = (
            self.__client.mget(batch)
            for batch in _batched(keys, self.__mget_count)
        )
        return (
            _unjelly(data)
            for data in chain.from_iterable(raw)
            if data is not None
        )

    def get(self, monitorid, configid, default=None):
        """Return the config data for the given config ID.

        If the config ID is not found, the default argument is returned.

        :type configid: str
        :type default: Any
        :rtype: Union[IJellyable, default]
        """
        key = self._makekey(monitorid, configid)
        if not self.__client.exists(key):
            return default
        return _unjelly(self.__client.get(key))

    def set(self, monitorid, configid, data):
        """Insert or replace the config data for the given config ID.

        If existing data for the configid exists under a different monitorid,
        it will be deleted.

        :param configid: The ID of the configuration
        :type configid: str
        :param data: The configuration object
        :type data: IJellyable
        :raises: ValueError
        """
        key = self._makekey(monitorid, configid)
        pattern = self._makekey("*", configid)
        deadkeys = tuple(
            key
            for key in self.__client.scan_iter(
                match=pattern, count=self.__scan_count
            )
            if key.split(":")[3] != monitorid
        )
        pipe = self.__client.pipeline()
        if deadkeys:
            pipe.delete(*deadkeys)
        pipe.set(key, jelly(data))
        pipe.execute()

    def delete(self, monitorid, configid):
        key = self._makekey(monitorid, configid)
        self.__client.delete(key)

    def mdelete(self, *configids):
        """Delete the configs associated with each of the given config IDs.

        :param configids: An iterable producing monitor ID/config IDs pairs
        :type configids: Iterable[(str, str)]
        """
        if not configids:
            return
        keys = (self._makekey(*cid) for cid in configids)
        self.__client.delete(*keys)


class MonitorDeviceMapStore(object):
    """
    Manages the mapping of device configurations to monitors.

    Configuration IDs are mapped to service ID/monitor ID pairs.

    A Service ID/monitor ID pair are used as a key to retrieve the
    Configuration IDs mapped to the pair.
    """

    # Implementation Note:
    # Locating a configuration ID requires searching each of the
    # service ID/monitor ID keys until the configuration ID is found.

    @classmethod
    def make(cls, service):
        """
        Create and return a MonitorDeviceMapStore to map configurations to
        service ID/monitor ID pairs.
        """
        client = getRedisClient(url=getRedisUrl())
        return cls(client, service)

    def __init__(self, client, service):
        """Initialize a MonitorDeviceMapStore instance.

        :param client: A Redis client instance.
        :type client: redis.StrictRedis
        :param service: The name of the configuration service.
        :type service: str
        """
        self.__client = client
        self.__template = "{app}:device:age:{{monitor}}:{service}".format(
            app=_app, service=service
        )
        self.__scan_count = 1000

    def search(self, monitorid="*"):
        """
        Return an iterable of tuples of (configId, last-update-timestamp).
        """
        if monitorid != "*":  # and serviceid != "*":
            key = self.__template.format(monitor=monitorid)
            return self.__client.zscan_iter(key, count=self.__scan_count)
        pattern = self.__template.format(monitor=monitorid)
        return (
            (cid, float(lastupdate) / 1000)
            for cid, lastupdate in chain.from_iterable(
                self.__client.zscan_iter(key, count=self.__scan_count)
                for key in self.__client.scan_iter(
                    match=pattern, count=self.__scan_count
                )
            )
        )

    def exists(self, monitorid, configid):
        key = self.__template.format(monitor=monitorid)
        return self.__client.zscore(key, configid) is not None

    def add(self, monitorid, configid):
        """
        Add a configid -> (monitorid, serviceid) mapping.
        This method will replace any existing mapping for configid.
        """
        pattern = self.__template.format(monitor="*")
        newkey = self.__template.format(monitor=monitorid)
        keys = self.__client.scan_iter(match=pattern, count=self.__scan_count)
        for key in keys:
            if self.__client.zscore(key, configid) is not None:
                _, _, _, oldmonitor, oldservice = key.split(":")
                tm = int(time.time() * 1000)
                if monitorid == oldmonitor:
                    self.__client.zadd(key, tm, configid)
                else:
                    pipe = self.__client.pipeline()
                    pipe.zrem(key, configid)
                    pipe.zadd(newkey, tm, configid)
                    pipe.execute()
                break
        else:
            tm = int(time.time() * 1000)
            self.__client.zadd(newkey, tm, configid)

    def remove(self, monitorid, configid):
        """
        Removes a configid from a (monitorid, serviceid) key.
        """
        key = self.__template.format(monitor=monitorid)
        self.__client.zrem(key, configid)


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
    # Note: In Python 3.7+, the above loop would be written as
    #     while (batch := tuple(islice(itr, n))):
    #         yield batch
