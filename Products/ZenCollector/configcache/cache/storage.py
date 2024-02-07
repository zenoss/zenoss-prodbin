##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
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
# modelchange:device:pending:<service>:<monitor> [(<score>, <device>), ...]
# modelchange:device:building:<service>:<monitor> [(<score>, <device>), ...]
#
# While "device" seems redundant, other values in this position could be
# "threshold" and "property".
#
# The "config" segment identifies a key storing a device configuration.
# The "age" segment identifies a key storing a set of device IDs sorted by
# a score that has an simple encoding.  The score is segmented by value.
# Values above zero are timestamps of when the current configuration was
# stored in redis.  A score of zero means the configuration is outdated
# and needs to be replaced with an updated version.  A score less than zero
# is the negated timestamp of when a request was submitted for a device
# configuration build.
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

from .model import ConfigKey, ConfigQuery, ConfigRecord, ConfigStatus

_app = "configcache"
log = logging.getLogger("zen.modelchange.stores")

_EXPIRED_SCORE = 0
_PENDING_SCORE = -1


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
        self.__uids = _DeviceUIDTable()
        self.__config = _DeviceConfigTable()
        self.__age = _ConfigMetadataTable("age")
        self.__retired = _ConfigMetadataTable("retired")
        self.__pending = _ConfigMetadataTable("pending")
        self.__building = _ConfigMetadataTable("building")
        self.__range = type(
            "rangefuncs",
            (object,),
            {
                "age": partial(_range, self.__client, self.__age),
                "retired": partial(_range, self.__client, self.__retired),
                "pending": partial(_range, self.__client, self.__pending),
                "building": partial(_range, self.__client, self.__building),
            },
        )()

    def search(self, query=ConfigQuery()):
        """
        Returns the configuration keys matching the search criteria.

        @type query: ConfigQuery
        @rtype: Iterator[ConfigKey]
        @raises TypeError: Unsupported value given for a field
        @raises AttributeError: Unknown field
        """
        if not isinstance(query, ConfigQuery):
            raise TypeError("'{!r} is not a ConfigQuery".format(query))
        return (
            ConfigKey(svc, mon, dvc)
            for svc, mon, dvc in self.__config.scan(
                self.__client, **attr.asdict(query)
            )
        )

    def add(self, record):
        """
        @type record: ConfigRecord
        """
        svc, mon, dvc, uid, updated, config = _from_record(record)

        orphaned_keys = tuple(
            key
            for key in self.search(ConfigQuery(service=svc, device=dvc))
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
                self.__pending.delete(pipe, *parts)
                self.__building.delete(pipe, *parts)
            if add_uid:
                self.__uids.set(pipe, dvc, uid)
            self.__config.set(pipe, svc, mon, dvc, config)
            self.__age.add(pipe, svc, mon, dvc, updated)
            self.__retired.delete(pipe, svc, mon, dvc)
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
        @type key: ConfigKey
        @rtype: ConfigRecord
        """
        conf = self.__config.get(
            self.__client, key.service, key.monitor, key.device
        )
        if conf is None:
            return default
        score = self.__age.score(
            self.__client, key.service, key.monitor, key.device
        )
        score = 0 if score < 0 else score
        uid = self.__uids.get(self.__client, key.device)
        return _to_record(
            key.service, key.monitor, key.device, uid, score, conf
        )

    def remove(self, *keys):
        """
        Delete the configurations identified by `keys`.

        @type keys: Sequence[ConfigKey]
        """
        with self.__client.pipeline() as pipe:
            for key in keys:
                svc, mon, dvc = key.service, key.monitor, key.device
                self.__config.delete(pipe, svc, mon, dvc)
                self.__age.delete(pipe, svc, mon, dvc)
                self.__retired.delete(pipe, svc, mon, dvc)
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

        A configuration is retired when its `updated` field is less than the
        difference between the current time and zDeviceConfigMinimumTTL.

        Only 'current' configurations can be marked as retired.  Attempts
        to change configurations in other statuses are ignored.

        @type keys: Sequence[ConfigKey]
        @rtype: Sequence[ConfigKey]
        """
        if len(keys) == 0:
            return ()

        not_retired = tuple(
            key
            for key in keys
            if not self.__retired.exists(
                self.__client, key.service, key.monitor, key.device
            )
        )
        if len(not_retired) == 0:
            return ()

        watch_keys = self._get_watch_keys(keys)
        targets = self._filter_by_score_keyonly(
            lambda x: x > _EXPIRED_SCORE, not_retired
        )
        if len(targets) == 0:
            return ()

        def _impl(pipe):
            pipe.multi()
            for svc, mon, dvc, score in targets:
                self.__retired.add(pipe, svc, mon, dvc, score)
                self.__pending.delete(pipe, svc, mon, dvc)
                self.__building.delete(pipe, svc, mon, dvc)

        self.__client.transaction(_impl, *watch_keys)
        return tuple(ConfigKey(svc, mon, dvc) for svc, mon, dvc, _ in targets)

    def set_expired(self, *keys):
        """
        Marks the indicated configuration as expired.

        Attempts to mark configurations that are not 'current' or
        'retired' are ignored.

        @type keys: Sequence[ConfigKey]
        @rtype: Sequence[ConfigKey]
        """
        if len(keys) == 0:
            return ()

        watch_keys = self._get_watch_keys(keys)
        targets = self._filter_by_score_keyonly(
            lambda x: x > _EXPIRED_SCORE, keys
        )
        if len(targets) == 0:
            return ()

        def _impl(pipe):
            pipe.multi()
            for svc, mon, dvc, _ in targets:
                self.__age.add(pipe, svc, mon, dvc, _EXPIRED_SCORE)
                self.__retired.delete(pipe, svc, mon, dvc)
                self.__pending.delete(pipe, svc, mon, dvc)
                self.__building.delete(pipe, svc, mon, dvc)

        self.__client.transaction(_impl, *watch_keys)
        return tuple(ConfigKey(svc, mon, dvc) for svc, mon, dvc, _ in targets)

    def set_pending(self, *pairs):
        """
        Marks an expired configuration as waiting for a new configuration.

        @type pending: Sequence[(ConfigKey, float)]
        @rtype: Sequence[ConfigKey]
        """
        if len(pairs) == 0:
            return ()

        watch_keys = self._get_watch_keys(key for key, _ in pairs)
        targets = self._filter_by_score_with_start(
            lambda x: x == _EXPIRED_SCORE, pairs
        )

        if len(targets) == 0:
            return ()

        def _impl(pipe):
            pipe.multi()
            for svc, mon, dvc, ts, _ in targets:
                score = _to_score(ts)
                self.__age.add(pipe, svc, mon, dvc, _PENDING_SCORE)
                self.__retired.delete(pipe, svc, mon, dvc)
                self.__building.delete(pipe, svc, mon, dvc)
                self.__pending.add(pipe, svc, mon, dvc, score)

        self.__client.transaction(_impl, *watch_keys)
        return tuple(
            ConfigKey(svc, mon, dvc) for svc, mon, dvc, _, _ in targets
        )

    def set_building(self, *pairs):
        """
        Marks a pending configuration as building a new configuration.

        @type pairs: Sequence[(ConfigKey, float)]
        @rtype: Sequence[ConfigKey]
        """
        if len(pairs) == 0:
            return ()

        valid = tuple(
            (key, ts)
            for key, ts in pairs
            if self.__pending.exists(
                self.__client, key.service, key.monitor, key.device
            )
        )
        if len(valid) == 0:
            return valid

        watch_keys = self._get_watch_keys(key for key, _ in valid)

        def _impl(pipe):
            pipe.multi()
            for key, ts in valid:
                svc = key.service
                mon = key.monitor
                dvc = key.device
                self.__pending.delete(pipe, svc, mon, dvc)
                self.__building.add(pipe, svc, mon, dvc, _to_score(ts))

        self.__client.transaction(_impl, *watch_keys)
        return tuple(key for key, _ in valid)

    def _filter_by_score_keyonly(self, predicate, keys):
        pairs = ((key, None) for key in keys)
        return tuple(
            (svc, mon, dvc, score)
            for svc, mon, dvc, _, score in self._filter_by_score(
                predicate, pairs
            )
        )

    def _filter_by_score_with_start(self, predicate, pairs):
        return tuple(self._filter_by_score(predicate, pairs))

    def _filter_by_score(self, predicate, pairs):
        scores = (
            (
                key,
                started,
                self.__age.score(
                    self.__client, key.service, key.monitor, key.device
                ),
            )
            for key, started in pairs
        )
        return (
            (key.service, key.monitor, key.device, started, score)
            for key, started, score in scores
            if predicate(score)
        )

    def get_status(self, *keys):
        """
        Returns an interable of (ConfigKey, ConfigStatus) tuples.

        @rtype: Iterable[Tuple[ConfigKey, ConfigStatus]]
        """
        scores = (
            (
                key,
                self.__age.score(
                    self.__client, key.service, key.monitor, key.device
                ),
            )
            for key in keys
        )
        return iter(self._iter_status(scores))

    def _iter_status(self, scores):
        for key, score in scores:
            if score > 0:
                rscore = self.__retired.score(
                    self.__client, key.service, key.monitor, key.device
                )
                if rscore is not None:
                    yield (key, ConfigStatus.Retired(_to_ts(rscore)))
                else:
                    yield (key, ConfigStatus.Current(_to_ts(score)))
            elif score == 0:
                yield (key, ConfigStatus.Expired())
            else:
                pscore = self.__pending.score(
                    self.__client, key.service, key.monitor, key.device
                )
                if pscore is not None:
                    yield (key, ConfigStatus.Pending(_to_ts(pscore)))
                bscore = self.__building.score(
                    self.__client, key.service, key.monitor, key.device
                )
                if bscore is not None:
                    yield (key, ConfigStatus.Building(_to_ts(bscore)))

    def get_building(self, service="*", monitor="*"):
        """
        Return an iterator producing (ConfigKey, ConfigStatus.Building) tuples.

        @rtype: Iterable[Tuple[ConfigKey, ConfigStatus.Building]]
        """
        return (
            (key, ConfigStatus.Building(ts))
            for key, ts in self.__range.building(service, monitor)
        )

    def get_pending(self, service="*", monitor="*"):
        """
        Return an iterator producing (ConfigKey, ConfigStatus.Pending) tuples.

        @rtype: Iterable[Tuple[ConfigKey, ConfigStatus.Pending]]
        """
        return (
            (key, ConfigStatus.Pending(ts))
            for key, ts in self.__range.pending(service, monitor)
        )

    def get_expired(self, service="*", monitor="*"):
        """
        Return an iterator producing (ConfigKey, ConfigStatus.Expired) tuples.

        @rtype: Iterable[Tuple[ConfigKey, ConfigStatus.Expired]]
        """
        return (
            (key, ConfigStatus.Expired())
            for key, _ in self.__range.age(
                service, monitor, minv=0.0, maxv=0.0
            )
        )

    def get_retired(self, service="*", monitor="*"):
        """
        Return an iterator producing (ConfigKey, ConfigStatus.Retired) tuples.

        @rtype: Iterable[Tuple[ConfigKey, ConfigStatus.Expired]]
        """
        return (
            (key, ConfigStatus.Retired(ts))
            for key, ts in self.__range.retired(service, monitor)
        )

    def get_older(self, maxtimestamp, service="*", monitor="*"):
        """
        Returns an iterator producing (ConfigKey, ConfigStatus.Current)
        tuples where current timestamp <= `maxtimestamp`.

        @rtype: Iterable[Tuple[ConfigKey, ConfigStatus.Current]]
        """
        # NOTE: 'older' means timestamps > 0 and <= `maxtimestamp`.
        return (
            (key, ConfigStatus.Current(ts))
            for key, ts in self.__range.age(
                service, monitor, minv="(0", maxv=_to_score(maxtimestamp)
            )
        )

    def get_newer(self, mintimestamp, service="*", monitor="*"):
        """
        Returns an iterator producing (ConfigKey, ConfigStatus.Current)
        tuples where current timestamp > `mintimestamp`.

        @rtype: Iterable[Tuple[ConfigKey, ConfigStatus.Current]]
        """
        # NOTE: 'newer' means timestamps  to `maxtimestamp`.
        return (
            (key, ConfigStatus.Current(ts))
            for key, ts in self.__range.age(
                service, monitor, minv="(%s" % (_to_score(mintimestamp),)
            )
        )

    def _get_watch_keys(self, keys):
        return set(
            itertools.chain.from_iterable(
                (
                    self.__age.make_key(key.service, key.monitor),
                    self.__retired.make_key(key.service, key.monitor),
                    self.__pending.make_key(key.service, key.monitor),
                    self.__building.make_key(key.service, key.monitor),
                )
                for key in keys
            )
        )


def _range(client, metadata, svc, mon, minv=None, maxv=None):
    pairs = metadata.get_pairs(client, svc, mon)
    return (
        (ConfigKey(svcId, monId, devId), _to_ts(score))
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
    key = ConfigKey(svc, mon, dvc)
    updated = _to_ts(updated)
    config = _unjelly(config)
    return ConfigRecord(key, uid, updated, config)


def _from_record(record):
    return (
        record.service,
        record.monitor,
        record.device,
        record.uid,
        _to_score(record.updated),
        jelly(record.config),
    )


class _DeviceUIDTable(object):
    """
    Manages mapping device names to their ZODB UID.
    """

    def __init__(self, scan_page_size=1000, mget_page_size=10):
        """Initialize a _DeviceUIDTable instance."""
        self.__template = "{app}:device:uid:{{device}}".format(app=_app)
        self.__scan_count = scan_page_size
        self.__mget_count = mget_page_size

    def make_key(self, device):
        return self.__template.format(device=device)

    def exists(self, client, device):
        """Return True if configuration data exists for the given ID.

        :param device: The ID of the device
        :type device: str
        :rtype: boolean
        """
        return client.exists(self.make_key(device))

    def scan(self, client, device="*"):
        """
        Return an iterable of tuples of device names.
        """
        pattern = self.make_key(device)
        result = client.scan_iter(match=pattern, count=self.__scan_count)
        return (key.rsplit(":", 1)[-1] for key in result)

    def get(self, client, device):
        """Return the UID of the given device name.

        :type device: str
        :rtype: str
        """
        key = self.make_key(device)
        return client.get(key)

    def set(self, client, device, uid):
        """Insert or replace the UID for the given device.

        :param device: The ID of the configuration
        :type device: str
        :param uid: The ZODB UID of the device
        :type uid: str
        :raises: ValueError
        """
        key = self.make_key(device)
        client.set(key, uid)

    def delete(self, client, *devices):
        """Delete one or more keys.

        This method does not fail if the key doesn't exist.

        :type uids: Sequence[str]
        """
        keys = tuple(self.make_key(dvc) for dvc in devices)
        client.delete(*keys)


class _DeviceConfigTable(object):
    """
    Manages device configuration data for a specific configuration service.
    """

    def __init__(self, scan_page_size=1000, mget_page_size=10):
        """Initialize a _DeviceConfigTable instance."""
        self.__template = (
            "{app}:device:config:{{service}}:{{monitor}}:{{device}}".format(
                app=_app
            )
        )
        self.__scan_count = scan_page_size
        self.__mget_count = mget_page_size

    def make_key(self, service, monitor, device):
        return self.__template.format(
            service=service, monitor=monitor, device=device
        )

    def exists(self, client, service, monitor, device):
        """Return True if configuration data exists for the given ID.

        :param service: Name of the configuration service.
        :type service: str
        :param monitor: Name of the monitor the device is a member of.
        :type monitor: str
        :param device: The ID of the device
        :type device: str
        :rtype: boolean
        """
        return client.exists(self.make_key(service, monitor, device))

    def scan(self, client, service="*", monitor="*", device="*"):
        """
        Return an iterable of tuples of (service, monitor, device).
        """
        pattern = self.make_key(service, monitor, device)
        result = client.scan_iter(match=pattern, count=self.__scan_count)
        return (tuple(key.rsplit(":", 3)[1:]) for key in result)

    def get(self, client, service, monitor, device):
        """Return the config data for the given config ID.

        If the config ID is not found, the default argument is returned.

        :type service: str
        :type monitor: str
        :type device: str
        :rtype: Union[IJellyable, None]
        """
        key = self.make_key(service, monitor, device)
        return client.get(key)

    def set(self, client, service, monitor, device, data):
        """Insert or replace the config data for the given config ID.

        If existing data for the device exists under a different monitor,
        it will be deleted.

        :param service: The name of the configuration service.
        :type service: str
        :param monitor: The ID of the performance monitor
        :type monitor: str
        :param device: The ID of the configuration
        :type device: str
        :param data: The serialized configuration data
        :type data: str
        :raises: ValueError
        """
        key = self.make_key(service, monitor, device)
        client.set(key, data)

    def delete(self, client, service, monitor, device):
        """Delete a key.

        This method does not fail if the key doesn't exist.

        :type service: str
        :type monitor: str
        :type device: str
        """
        key = self.make_key(service, monitor, device)
        client.delete(key)


class _ConfigMetadataTable(object):
    """
    Manages the mapping of device configurations to monitors.

    Configuration IDs are mapped to service ID/monitor ID pairs.

    A Service ID/monitor ID pair are used as a key to retrieve the
    Configuration IDs mapped to the pair.
    """

    def __init__(self, category):
        """Initialize a ConfigMetadataStore instance."""
        self.__template = (
            "{app}:device:{category}:{{service}}:{{monitor}}".format(
                app=_app, category=category
            )
        )
        self.__scan_count = 1000

    def make_key(self, service, monitor):
        return self.__template.format(service=service, monitor=monitor)

    def get_pairs(self, client, service="*", monitor="*"):
        pattern = self.make_key(service, monitor)
        return (
            key.rsplit(":", 2)[1:]
            for key in client.scan_iter(match=pattern, count=self.__scan_count)
        )

    def scan(self, client, pairs):
        """
        Return an iterable of tuples of (service, monitor, device, score).

        @type client: redis client
        @type pairs: Iterable[Tuple[str, str]]
        @rtype Iterator[Tuple[str, str, str, float]]
        """
        return (
            (service, monitor, dvc, score)
            for service, monitor in pairs
            for dvc, score in client.zscan_iter(
                self.make_key(service, monitor), count=self.__scan_count
            )
        )

    def range(self, client, pairs, maxscore=None, minscore=None):
        """
        Return an iterable of tuples of (service, monitor, device, score).

        @type client: redis client
        @type pairs: Iterable[Tuple[str, str]]
        @type minscore: Union[float, None]
        @type maxscore: Union[float, None]
        @rtype Iterator[Tuple[str, str, str, float]]
        """
        maxv = maxscore if maxscore is not None else "+inf"
        minv = minscore if minscore is not None else "-inf"
        return (
            (service, monitor, device, score)
            for service, monitor in pairs
            for device, score in client.zrangebyscore(
                self.make_key(service, monitor), minv, maxv, withscores=True
            )
        )

    def exists(self, client, service, monitor, device):
        """Return True if a score for the key and device exists.

        @type client: RedisClient
        @type service: str
        @type monitor: str
        @type device: str
        """
        key = self.make_key(service, monitor)
        return client.zscore(key, device) is not None

    def add(self, client, service, monitor, device, score):
        """
        Add a (device, score) -> (monitor, serviceid) mapping.
        This method will replace any existing mapping for device.

        @type client: RedisClient
        @type service: str
        @type monitor: str
        @type device: str
        @type score: float
        """
        key = self.make_key(service, monitor)
        client.zadd(key, score, device)

    def score(self, client, service, monitor, device):
        """
        Returns the timestamp associated with the device ID.
        Returns None of the device ID is not found.
        """
        key = self.make_key(service, monitor)
        return client.zscore(key, device)

    def delete(self, client, service, monitor, device):
        """
        Removes a device from a (service, monitor) key.
        """
        key = self.make_key(service, monitor)
        client.zrem(key, device)


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
