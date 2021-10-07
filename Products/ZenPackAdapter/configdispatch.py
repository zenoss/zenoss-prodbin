##############################################################################
#
# Copyright (C) Zenoss, Inc. 2021, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging
from collections import defaultdict
from functools import partial
import mmh3
import math

import zope.component
from zope.interface import implements

from Products.ZenCollector.interfaces import (
    IConfigurationDispatchingFilter,
    ICollectorPreferences
)

LOG = logging.getLogger("zen.configdispatch")

_WPOOL = None
def getWorkerDispatchPool():
    global _WPOOL

    if _WPOOL is None:
        _WPOOL = WorkerPool()
    return _WPOOL

def type_and_id(options):
    collectorType = options.get('zpaCollectorType', 'None')
    collectorId = options.get('zpaCollectorId', 1)

    return collectorType, collectorId

def int_to_float(value):
    fifty_three_ones = (0xFFFFFFFFFFFFFFFF >> (64-53))
    fifty_three_zeros = float(1 << 53)
    return (value & fifty_three_ones) / fifty_three_zeros

class WRHBucket(object):
    bucketId = None
    weight = None

    def __init__(self, bucketId, weight):
        self.bucketId, self.weight = bucketId, weight

    def compute_weighted_score(self, key):
        hash1, hash2 = mmh3.hash64(str(self.bucketId + "/" + key))
        score = 1.0 / -math.log(int_to_float(hash2))
        return self.weight * score

class WRH(object):
    buckets = None

    def __init__(self, buckets=None):
        if buckets is None:
            buckets = []

        self.buckets = {}

        for bucket in buckets:
            self.buckets[bucket.bucketId] = bucket

    def add_bucket(self, bucketId, weight=1.0):
        self.buckets[bucketId] = WRHBucket(bucketId, weight)

    def remove_bucket(self, bucketId):
        if bucketId in self.buckets:
            del self.buckets[bucketId]

    def determine_responsible_bucket(self, key):
        champion, highest_score = None, -1
        for bucket in self.buckets.values():
            score = bucket.compute_weighted_score(key)
            if score > highest_score:
                champion, highest_score = bucket, score

        return champion


class WorkerPool(object):
    workers = None

    def __init__(self):
        self.workers = defaultdict(WRH)

    def add_worker(self, options):
        collectorType, collectorId = type_and_id(options)
        self.workers[collectorType].add_bucket(collectorId)
        LOG.info("Added new %s worker: %s", collectorType, collectorId)

    def remove_worker(self, options):
        collectorType, collectorId = type_and_id(options)
        self.workers[collectorType].remove_bucket(collectorId)
        LOG.info("Removed %s worker: %s", collectorType, collectorId)

    def get_workers(self, collectorType):
        return [x for x in self.workers[collectorType].buckets]

    def collectorId_for_deviceId(self, deviceId, options):
        collectorType, _ = type_and_id(options)

        wrh = self.workers[collectorType]
        bucket = wrh.determine_responsible_bucket(deviceId)

        return bucket.bucketId



# IMPORTANT NOTE: One of the concepts behind the rendezvous hash
# is that it can produce the same results across multiple
# instances, as long as they have the same members.
#
# There is one instance of the IConfigurationDispatchingFilter utility used
# used for config dispatching in zminihub (one per
# service, technically), but there can also be one in each collector daemon.
#
# I had intended to do this by using a setPropertyItems remote
# call to push the list of pool members down whenever it changes.
#
# I decided that this wasn't necessary, though, because that
# collector-daemon side filtering wasn't really required.  As
# long as zminihub is pushing the right configs to the right
# daemons, they don't really need to double-check it.  So the collector
# daemons do not have dispatch filtering turned on.

class RendezvousHashDispatchingFilter(object):
    implements(IConfigurationDispatchingFilter)

    def getFilter(self, options):
        collectorType, collectorId = type_and_id(options)
        pool = getWorkerDispatchPool()

        def _filter(collectorType, collectorId, device):
            deviceId = getattr(device, 'id', '')
            return collectorId == pool.collectorId_for_deviceId(deviceId, options)

        return partial(_filter, collectorType, collectorId)

