##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
from time import time
from itertools import chain
from functools import wraps

from twisted.internet.defer import inlineCallbacks
from zope.component import getUtility, getUtilitiesFor, subscribers
from ZODB.POSException import POSKeyError

from zenoss.protocols.protobufs.zep_pb2 import (
    SEVERITY_CRITICAL, SEVERITY_CLEAR
)

import Globals  # required to import zenoss Products
from Products.ZenUtils.Utils import unused

from Products.ZenRelations.PrimaryPathObjectManager import (
    PrimaryPathObjectManager
)
from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.ZenHub.invalidations import INVALIDATIONS_PAUSED
from Products.ZenHub.interfaces import (
    IInvalidationProcessor,
    IInvalidationFilter,
    FILTER_INCLUDE,
    FILTER_EXCLUDE,
    IInvalidationOid,
)

unused(Globals)

log = logging.getLogger('zen.ZenHub.invalidationmanager')


class InvalidationManager(object):

    _invalidation_paused_event = {
        'summary': "Invalidation processing is "
                   "currently paused. To resume, set "
                   "'dmd.pauseHubNotifications = False'",
        'severity': SEVERITY_CRITICAL,
        'eventkey': INVALIDATIONS_PAUSED
    }

    _invalidation_unpaused_event = {
        'summary': 'Invalidation processing unpaused',
        'severity': SEVERITY_CLEAR,
        'eventkey': INVALIDATIONS_PAUSED
    }

    def __init__(
        self, dmd, log,
        syncdb, poll_invalidations, send_event,
        poll_interval=30
    ):
        self.__dmd = dmd
        self.__syncdb = syncdb
        self.log = log
        self.__poll_invalidations = poll_invalidations
        self.__send_event = send_event
        self.poll_interval = poll_interval

        self._currently_paused = False
        self.totalEvents = 0
        self.totalTime = 0

        self.initialize_invalidation_filters()
        self.processor = getUtility(IInvalidationProcessor)
        log.debug('got InvalidationProcessor %s' % self.processor)
        app = self.__dmd.getPhysicalRoot()
        self.invalidation_pipeline = InvalidationPipeline(
            app, self._invalidation_filters, self.processor
        )

    def initialize_invalidation_filters(self):
        '''Get Invalidation Filters, initialize them,
        store them in the _invalidation_filters list, and return the list
        '''
        try:
            filters = (f for n, f in getUtilitiesFor(IInvalidationFilter))
            self._invalidation_filters = []
            for fltr in sorted(
                filters, key=lambda f: getattr(f, 'weight', 100)
            ):
                fltr.initialize(self.__dmd)
                self._invalidation_filters.append(fltr)
            self.log.debug('Registered %s invalidation filters.',
                           len(self._invalidation_filters))
            return self._invalidation_filters
        except Exception:
            log.exception('error in initialize_invalidation_filters')

    @inlineCallbacks
    def process_invalidations(self):
        '''Periodically process database changes.
        synchronize with the database, and poll invalidated oids from it,
        filter the oids,  send them to the invalidation_processor

        @return: None
        '''
        try:
            now = time()
            yield self._syncdb()
            if self._paused():
                return

            oids = self._poll_invalidations()
            if not oids:
                log.debug('no invalidations found: oids=%s' % oids)
                return

            for oid in oids:
                yield self.invalidation_pipeline.run(oid)

            self.log.debug('Processed %s raw invalidations', len(oids))

        except Exception:
            log.exception('error in process_invalidations')
        finally:
            self.totalEvents += 1
            self.totalTime += time() - now
            log.debug('end process_invalidations')

    @inlineCallbacks
    def _syncdb(self):
        try:
            self.log.debug("[processQueue] syncing....")
            yield self.__syncdb()
            self.log.debug("[processQueue] synced")
        except Exception as err:
            self.log.warn("Unable to poll invalidations, will try again.")

    def _paused(self):
        if not self._currently_paused:
            if self.__dmd.pauseHubNotifications:
                self._currently_paused = True
                log.info('notifications have been paused')
                self._send_event(self._invalidation_paused_event)
                return True
            else:
                return False

        else:
            if self.__dmd.pauseHubNotifications:
                log.debug('notifications are paused')
                return True
            else:
                self._currently_paused = False
                log.info('notifications unpaused')
                self._send_event(self._invalidation_unpaused_event)
                return False

    def _poll_invalidations(self):
        '''pull a list of invalidated object oids from the database
        '''
        try:
            log.debug('poll invalidations from dmd.storage')
            return self.__poll_invalidations()
        except Exception:
            log.exception('error in _poll_invalidations')

    @inlineCallbacks
    def _send_event(self, event):
        yield self.__send_event(event)


class InvalidationPipeline(object):
    '''A Pipeline that applies filters and transforms to an oid
    Then passes the transformed/expanded list of oids
    to the InvalidationProcessor processQueue
    '''

    def __init__(self, app, filters, processor):
        self.__pipeline = oid_to_obj(
            app, processor,
            filter_obj(
                filters,
                transform_obj(
                    processor
                )
            )
        )

    def run(self, invalidation):
        self.__pipeline.send(invalidation)


def coroutine(func):
    """Decorator for initializing a generator as a coroutine.
    """
    @wraps(func)
    def start(*args, **kw):
        coro = func(*args, **kw)
        coro.next()
        return coro
    return start


@coroutine
def iterate(target):
    """iterates over the iterable, sending each produced item to the target.
    """
    while True:
        iterable = (yield)
        for item in iterable:
            target.send(item)


@coroutine
def oid_to_obj(app, processor, checker):
    while True:
        oid = (yield)
        # Include oids that are missing from the database
        try:
            obj = app._p_jar[oid]
        except POSKeyError:
            processor.processQueue([oid])
            continue
        # Exclude any unmatched types
        if not isinstance(obj, (PrimaryPathObjectManager, DeviceComponent)):
            continue
        # Include deleted oids
        try:
            obj = obj.__of__(app.zport.dmd).primaryAq()
        except (AttributeError, KeyError):
            processor.processQueue([oid])
            continue

        checker.send((oid, obj))


@coroutine
def filter_obj(filters, target):
    while True:
        oid, obj = (yield)
        included = True
        for fltr in filters:
            result = fltr.include(obj)
            if result is FILTER_INCLUDE:
                break
            if result is FILTER_EXCLUDE:
                included = False
                break
        if included:
            target.send((oid, obj))


@coroutine
def transform_obj(processor):
    while True:
        oid, obj = (yield)

        # First, get any subscription adapters registered as transforms
        adapters = subscribers((obj,), IInvalidationOid)
        # Next check for an old-style (regular adapter) transform
        try:
            adapters = chain(adapters, (IInvalidationOid(obj),))
        except TypeError:
            # No old-style adapter is registered
            pass
        transformed = set()
        for adapter in adapters:
            o = adapter.transformOid(oid)
            if isinstance(o, str):
                transformed.add(o)
            elif hasattr(o, '__iter__'):
                # If the transform didn't give back a string, it should have
                # given back an iterable
                transformed.update(o)
        # Get rid of any useless Nones
        transformed.discard(None)
        # Get rid of the original oid, if returned. We don't want to use it IF
        # any transformed oid came back.
        transformed.discard(oid)
        processor.processQueue(transformed or (oid,))
