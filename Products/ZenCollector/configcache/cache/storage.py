##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

# Key structure
# =============
# modelchange:device:uid:<device> <uid>
# modelchange:device:config:<service>:<monitor>:<device> <config>
# modelchange:device:age:<service>:<monitor> [(<score>, <device>), ...]
# modelchange:device:retired:<service>:<monitor> [(<score>, <device>), ...]
# modelchange:device:expired:<service>:<monitor> [(<score>, <device>), ...]
# modelchange:device:pending:<service>:<monitor> [(<score>, <device>), ...]
# modelchange:device:building:<service>:<monitor> [(<score>, <device>), ...]
#
# While "device" seems redundant, other values in this position could be
# "threshold" and "property".
#
# * uid - Maps a device to its object path in ZODB
# * config - Maps a key (<service>:<monitor>:<device>) to a configuration
# * age - Stores the timestamp for when the configuration was created
#
# The following keys store the state of a device's config.
#
# * retired - devices with a 'retired' config.
#
#      The <score> is a copy from the 'age' key.  Since retirement is
#      controlled by a z-property, storing the time when the config
#      transitioned to 'retire' is not useful because the z-property
#      can change dynamically.
#
# * expired - devices with an 'expired' config.
#
#      The <score> is the timestamp when the config was expired.
#
# * pending - devices with a 'pending' config
#
#      The <score> is the timestamp when the build_device_config job
#      was submitted.
#
# * building - devices with a 'building' config
#
#      The <score> is the timestamp when the build_device_config job
#      began execution.
#
# A device may exist in only one of 'retired', 'expired', 'pending',
# 'building', or none of them.
#
# <service> names the configuration service class used to generate the
# configuration.
# <monitor> names the monitor (collector) the device belongs to.
# <device> is the ID of the device
# <uid> is the object path to the device in ZODB.
#

from __future__ import absolute_import, print_function, division

import ast
import logging
import itertools

from functools import partial
from itertools import islice

import attr

from twisted.spread.jelly import jelly, unjelly
from zope.component.factory import Factory

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

from .model import CacheKey, CacheQuery, CacheRecord, ConfigStatus
from .table import DeviceUIDTable, DeviceConfigTable, ConfigMetadataTable

_app = "configcache"
log = logging.getLogger("zen.modelchange.stores")


class ConfigStoreFactory(Factory):
    """
    IFactory implementation for ConfigStore objects.
    """

    def __init__(self):
        super(ConfigStoreFactory, self).__init__(
            ConfigStore, "ConfigStore", "Configuration Cache Storage"
        )


class ConfigStore(object):
    """
    A device config store for a single configuration class.
    """

    @classmethod
    def make(cls):
        """Create and return a ConfigStore object."""
        client = getRedisClient(url=getRedisUrl())
        return cls(client)

    def __init__(self, client):
        """Initialize a ConfigStore instance."""
        self.__client = client
        self.__uids = DeviceUIDTable(_app)
        self.__config = DeviceConfigTable(_app)
        self.__age = ConfigMetadataTable(_app, "age")
        self.__retired = ConfigMetadataTable(_app, "retired")
        self.__expired = ConfigMetadataTable(_app, "expired")
        self.__pending = ConfigMetadataTable(_app, "pending")
        self.__building = ConfigMetadataTable(_app, "building")
        self.__range = type(
            "rangefuncs",
            (object,),
            {
                "age": partial(_range, self.__client, self.__age),
                "retired": partial(_range, self.__client, self.__retired),
                "expired": partial(_range, self.__client, self.__expired),
                "pending": partial(_range, self.__client, self.__pending),
                "building": partial(_range, self.__client, self.__building),
            },
        )()

    def search(self, query=CacheQuery()):
        """
        Returns the configuration keys matching the search criteria.

        @type query: CacheQuery
        @rtype: Iterator[CacheKey]
        @raises TypeError: Unsupported value given for a field
        @raises AttributeError: Unknown field
        """
        if not isinstance(query, CacheQuery):
            raise TypeError("'{!r} is not a CacheQuery".format(query))
        return (
            CacheKey(svc, mon, dvc)
            for svc, mon, dvc in self.__config.scan(
                self.__client, **attr.asdict(query)
            )
        )

    def add(self, record):
        """
        @type record: CacheRecord
        """
        svc, mon, dvc, uid, updated, config = _from_record(record)

        orphaned_keys = tuple(
            key
            for key in self.search(CacheQuery(service=svc, device=dvc))
            if key.monitor != mon
        )
        watch_keys = self._get_watch_keys(orphaned_keys + (record.key,))
        add_uid = not self.__uids.exists(self.__client, dvc)

        def _add_impl(pipe):
            pipe.multi()
            # Remove configs for this device that exist with a different
            # monitor.
            # Note: configs produced by different configuration services
            # may exist simultaneously.
            for key in orphaned_keys:
                parts = (key.service, key.monitor, key.device)
                self.__config.delete(pipe, *parts)
                self.__age.delete(pipe, *parts)
                self.__retired.delete(pipe, *parts)
                self.__expired.delete(pipe, *parts)
                self.__pending.delete(pipe, *parts)
                self.__building.delete(pipe, *parts)
            if add_uid:
                self.__uids.set(pipe, dvc, uid)
            self.__config.set(pipe, svc, mon, dvc, config)
            self.__age.add(pipe, svc, mon, dvc, updated)
            self.__retired.delete(pipe, svc, mon, dvc)
            self.__expired.delete(pipe, svc, mon, dvc)
            self.__pending.delete(pipe, svc, mon, dvc)
            self.__building.delete(pipe, svc, mon, dvc)

        self.__client.transaction(_add_impl, *watch_keys)

    def get_uid(self, device):
        """
        Return the ZODB UID (path) for the given device.

        @type device: str
        """
        return self.__uids.get(self.__client, device)

    def get(self, key, default=None):
        """
        @type key: CacheKey
        @rtype: CacheRecord
        """
        with self.__client.pipeline() as pipe:
            self.__config.get(pipe, key.service, key.monitor, key.device)
            self.__age.score(pipe, key.service, key.monitor, key.device)
            self.__uids.get(pipe, key.device)
            conf, score, uid = pipe.execute()
        if conf is None:
            return default
        score = 0 if score < 0 else score
        return _to_record(
            key.service, key.monitor, key.device, uid, score, conf
        )

    def remove(self, *keys):
        """
        Delete the configurations identified by `keys`.

        @type keys: Sequence[CacheKey]
        """
        with self.__client.pipeline() as pipe:
            for key in keys:
                svc, mon, dvc = key.service, key.monitor, key.device
                self.__config.delete(pipe, svc, mon, dvc)
                self.__age.delete(pipe, svc, mon, dvc)
                self.__retired.delete(pipe, svc, mon, dvc)
                self.__expired.delete(pipe, svc, mon, dvc)
                self.__pending.delete(pipe, svc, mon, dvc)
                self.__building.delete(pipe, svc, mon, dvc)
            pipe.execute()
        devices = []
        for dvc in set(k.device for k in keys):
            configs = tuple(self.__config.scan(self.__client, device=dvc))
            if not configs:
                devices.append(dvc)
        if devices:
            self.__uids.delete(self.__client, *devices)

    def set_retired(self, *keys):
        """
        Marks the indicated configuration as retired.

        The keys that were retired are returned to the caller.  The returned
        keys may match or be a subset of the keys that were passed in.

        If a config is already retired, it will not be among the keys
        that are returned.

        @type keys: Sequence[CacheKey]
        @rtype: Sequence[CacheKey]
        """
        if len(keys) == 0:
            return ()

        not_retired = tuple(
            self._filter_existing(self.__retired, keys, lambda x: x)
        )
        if len(not_retired) == 0:
            return ()

        watch_keys = self._get_watch_keys(not_retired)
        scores = (
            (
                key,
                self.__age.score(
                    self.__client, key.service, key.monitor, key.device
                ),
            )
            for key in not_retired
        )
        targets = (
            (key.service, key.monitor, key.device, score)
            for key, score in scores
        )

        def _impl(pipe):
            pipe.multi()
            for svc, mon, dvc, score in targets:
                self.__retired.add(pipe, svc, mon, dvc, score)
                self.__expired.delete(pipe, svc, mon, dvc)
                self.__pending.delete(pipe, svc, mon, dvc)
                self.__building.delete(pipe, svc, mon, dvc)

        self.__client.transaction(_impl, *watch_keys)
        return not_retired

    def set_expired(self, *pairs):
        """
        Marks the indicated configuration as expired.

        The keys that were expired are returned to the caller.  The returned
        keys may match or be a subset of the keys that were passed in.

        If a config is already expired, it will not be among the keys
        that are returned.

        @type keys: Sequence[(CacheKey, float)]
        @rtype: Sequence[CacheKey]
        """
        if len(pairs) == 0:
            return ()

        not_expired = tuple(
            self._filter_existing(self.__expired, pairs, lambda x: x[0])
        )
        if len(not_expired) == 0:
            return ()

        watch_keys = self._get_watch_keys(key for key, _ in not_expired)
        targets = (
            (key.service, key.monitor, key.device, ts)
            for key, ts in not_expired
        )

        def _impl(pipe):
            pipe.multi()
            for svc, mon, dvc, ts in targets:
                score = _to_score(ts)
                self.__retired.delete(pipe, svc, mon, dvc)
                self.__expired.add(pipe, svc, mon, dvc, score)
                self.__pending.delete(pipe, svc, mon, dvc)
                self.__building.delete(pipe, svc, mon, dvc)

        self.__client.transaction(_impl, *watch_keys)
        return tuple(key for key, _ in not_expired)

    def set_pending(self, *pairs):
        """
        Marks a configuration as waiting for a new configuration.

        The keys that were marked pending are returned to the caller.
        The returned keys may match or be a subset of the keys that
        were passed in.

        If a config is already marked pending, it will not be among the
        keys that are returned.

        @type pending: Sequence[(CacheKey, float)]
        @rtype: Sequence[CacheKey]
        """
        if len(pairs) == 0:
            return ()

        not_pending = tuple(
            self._filter_existing(self.__pending, pairs, lambda x: x[0])
        )
        if len(not_pending) == 0:
            return ()

        watch_keys = self._get_watch_keys(key for key, _ in not_pending)
        targets = (
            (key.service, key.monitor, key.device, ts)
            for key, ts in not_pending
        )

        def _impl(pipe):
            pipe.multi()
            for svc, mon, dvc, ts in targets:
                score = _to_score(ts)
                self.__retired.delete(pipe, svc, mon, dvc)
                self.__expired.delete(pipe, svc, mon, dvc)
                self.__pending.add(pipe, svc, mon, dvc, score)
                self.__building.delete(pipe, svc, mon, dvc)

        self.__client.transaction(_impl, *watch_keys)
        return tuple(key for key, _ in not_pending)

    def set_building(self, *pairs):
        """
        Marks a configuration as building a new configuration.

        The keys that were marked building are returned to the caller.
        The returned keys may match or be a subset of the keys that
        were passed in.

        If a config is already marked building, it will not be among the
        keys that are returned.

        @type pairs: Sequence[(CacheKey, float)]
        @rtype: Sequence[CacheKey]
        """
        if len(pairs) == 0:
            return ()

        not_building = tuple(
            self._filter_existing(self.__building, pairs, lambda x: x[0])
        )
        if len(not_building) == 0:
            return ()

        watch_keys = self._get_watch_keys(key for key, _ in not_building)
        targets = (
            (key.service, key.monitor, key.device, ts)
            for key, ts in not_building
        )

        def _impl(pipe):
            pipe.multi()
            for svc, mon, dvc, ts in targets:
                score = _to_score(ts)
                self.__retired.delete(pipe, svc, mon, dvc)
                self.__expired.delete(pipe, svc, mon, dvc)
                self.__pending.delete(pipe, svc, mon, dvc)
                self.__building.add(pipe, svc, mon, dvc, score)

        self.__client.transaction(_impl, *watch_keys)
        return tuple(key for key, _ in not_building)

    def _filter_existing(self, table, items, getkey):
        for item in items:
            key = getkey(item)
            if not table.exists(
                self.__client, key.service, key.monitor, key.device
            ):
                yield item

    def get_status(self, *keys):
        """
        Returns an interable of ConfigStatus objects.

        @rtype: Iterable[ConfigStatus]
        """
        for key in keys:
            scores = self._get_scores(key)
            uid = self.__uids.get(self.__client, key.device)
            status = self._get_status(scores, key, uid)
            if status is not None:
                yield status

    def get_building(self, service="*", monitor="*"):
        """
        Return an iterator producing ConfigStatus.Building objects.

        @rtype: Iterable[ConfigStatus.Building]
        """
        return (
            ConfigStatus.Building(
                key, self.__uids.get(self.__client, key.device), ts
            )
            for key, ts in self.__range.building(service, monitor)
        )

    def get_pending(self, service="*", monitor="*"):
        """
        Return an iterator producing ConfigStatus.Pending objects.

        @rtype: Iterable[ConfigStatus.Pending]
        """
        return (
            ConfigStatus.Pending(
                key, self.__uids.get(self.__client, key.device), ts
            )
            for key, ts in self.__range.pending(service, monitor)
        )

    def get_expired(self, service="*", monitor="*"):
        """
        Return an iterator producing ConfigStatus.Expired objects.

        @rtype: Iterable[ConfigStatus.Expired]
        """
        return (
            ConfigStatus.Expired(
                key, self.__uids.get(self.__client, key.device), ts
            )
            for key, ts in self.__range.expired(service, monitor)
        )

    def get_retired(self, service="*", monitor="*"):
        """
        Return an iterator producing ConfigStatus.Retired objects.

        @rtype: Iterable[ConfigStatus.Retired]
        """
        return (
            ConfigStatus.Retired(
                key, self.__uids.get(self.__client, key.device), ts
            )
            for key, ts in self.__range.retired(service, monitor)
        )

    def get_older(self, maxtimestamp, service="*", monitor="*"):
        """
        Returns an iterator producing ConfigStatus.Current objects
        where current timestamp <= `maxtimestamp`.

        @rtype: Iterable[ConfigStatus.Current]
        """
        # NOTE: 'older' means timestamps > 0 and <= `maxtimestamp`.
        selection = tuple(
            (key, age)
            for key, age in self.__range.age(
                service, monitor, minv="(0", maxv=_to_score(maxtimestamp)
            )
        )
        for key, age in selection:
            scores = self._get_scores(key)[1:]
            if any(score is not None for score in scores):
                continue
            uid = self.__uids.get(self.__client, key.device)
            yield ConfigStatus.Current(key, uid, age)

    def get_newer(self, mintimestamp, service="*", monitor="*"):
        """
        Returns an iterator producing ConfigStatus.Current objects
        where current timestamp > `mintimestamp`.

        @rtype: Iterable[ConfigStatus.Current]
        """
        # NOTE: 'newer' means timestamps  to `maxtimestamp`.
        selection = tuple(
            (key, age)
            for key, age in self.__range.age(
                service, monitor, minv="(%s" % (_to_score(mintimestamp),)
            )
        )
        for key, age in selection:
            scores = self._get_scores(key)[1:]
            if any(score is not None for score in scores):
                continue
            uid = self.__uids.get(self.__client, key.device)
            yield ConfigStatus.Current(key, uid, age)

    def _get_scores(self, key):
        service, monitor, device = attr.astuple(key)
        with self.__client.pipeline() as pipe:
            self.__age.score(pipe, service, monitor, device),
            self.__retired.score(pipe, service, monitor, device),
            self.__expired.score(pipe, service, monitor, device),
            self.__pending.score(pipe, service, monitor, device),
            self.__building.score(pipe, service, monitor, device),
            return pipe.execute()

    def _get_status(self, scores, key, uid):
        age, retired, expired, pending, building = scores
        if building is not None:
            return ConfigStatus.Building(key, uid, _to_ts(building))
        elif pending is not None:
            return ConfigStatus.Pending(key, uid, _to_ts(pending))
        elif expired is not None:
            return ConfigStatus.Expired(key, uid, _to_ts(expired))
        elif retired is not None:
            return ConfigStatus.Retired(key, uid, _to_ts(retired))
        elif age is not None:
            return ConfigStatus.Current(key, uid, _to_ts(age))

    def _get_watch_keys(self, keys):
        return set(
            itertools.chain.from_iterable(
                (
                    self.__age.make_key(key.service, key.monitor),
                    self.__retired.make_key(key.service, key.monitor),
                    self.__expired.make_key(key.service, key.monitor),
                    self.__pending.make_key(key.service, key.monitor),
                    self.__building.make_key(key.service, key.monitor),
                )
                for key in keys
            )
        )


def _range(client, metadata, svc, mon, minv=None, maxv=None):
    pairs = metadata.get_pairs(client, svc, mon)
    return (
        (CacheKey(svcId, monId, devId), _to_ts(score))
        for svcId, monId, devId, score in metadata.range(
            client, pairs, minscore=minv, maxscore=maxv
        )
    )


def _unjelly(data):
    return unjelly(ast.literal_eval(data))


def _to_score(ts):
    return ts * 1000.0


def _to_ts(score):
    return score / 1000.0


def _to_record(svc, mon, dvc, uid, updated, config):
    key = CacheKey(svc, mon, dvc)
    updated = _to_ts(updated)
    config = _unjelly(config)
    return CacheRecord(key, uid, updated, config)


def _from_record(record):
    return (
        record.service,
        record.monitor,
        record.device,
        record.uid,
        _to_score(record.updated),
        jelly(record.config),
    )


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
