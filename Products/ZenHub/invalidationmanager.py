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

        self._invalidations_paused = False
        self.totalEvents = 0
        self.totalTime = 0

        self.initialize_invalidation_filters()
        self.processor = getUtility(IInvalidationProcessor)
        log.debug('got InvalidationProcessor %s' % self.processor)

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
            oids = self._poll_invalidations()
            if not oids:
                log.debug('no invalidations found: oids=%s' % oids)
                return
            oids = self._filter_oids(oids)
            if not oids:
                log.debug('filter returned no oids')
                return

            ret = self.processor.processQueue(tuple(set(oids)))
            result = getattr(ret, 'result', None)
            if not result:
                result = ret
            log.debug('finished processing oids')
            if result == INVALIDATIONS_PAUSED:
                self._send_event(self._invalidation_paused_event)
                self._invalidations_paused = True
            else:
                msg = 'Processed %s oids' % result
                self.log.debug(msg)
                if self._invalidations_paused:
                    self.send_invalidations_unpaused_event(msg)
                    self._invalidations_paused = False

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

    def _poll_invalidations(self):
        try:
            log.debug('poll invalidations from dmd.storage')
            return self.__poll_invalidations()
        except Exception:
            log.exception('error in _poll_invalidations')

    def _filter_oids(self, oids):
        try:
            app = self.__dmd.getPhysicalRoot()
            for oid in oids:
                obj = self._oid_to_object(app, oid)
                if obj is FILTER_INCLUDE:
                    yield oid
                    continue
                if obj is FILTER_EXCLUDE:
                    continue

                # Filter all remaining oids
                include = self._apply_filters(obj)
                if include:
                    _oids = self._transformOid(oid, obj)
                    for _oid in _oids:
                        yield _oid
        except Exception:
            log.exception('error in _filter_oids')

    def _oid_to_object(self, app, oid):
        # Include oids that are missing from the database
        try:
            obj = app._p_jar[oid]
        except POSKeyError:
            return FILTER_INCLUDE

        # Exclude any unmatched types
        if not isinstance(
            obj, (PrimaryPathObjectManager, DeviceComponent)
        ):
            return FILTER_EXCLUDE

        # Include deleted oids
        try:
            obj = obj.__of__(self.__dmd).primaryAq()
        except (AttributeError, KeyError):
            return FILTER_INCLUDE

        return obj

    def _apply_filters(self, obj):
        for fltr in self._invalidation_filters:
            result = fltr.include(obj)
            if result is FILTER_INCLUDE:
                return True
            if result is FILTER_EXCLUDE:
                return False
        return True

    @staticmethod
    def _transformOid(oid, obj):
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
            if isinstance(o, basestring):
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
        return transformed or (oid,)

    @inlineCallbacks
    def _send_event(self, event):
        yield self.__send_event(event)

    def _send_invalidations_unpaused_event(self, msg):
        self._send_event({
            'summary': msg,
            'severity': SEVERITY_CLEAR,
            'eventkey': INVALIDATIONS_PAUSED
        })

    def _doProcessQueue(self):
        """
        Perform one cycle of update notifications.

        @return: None
        """
        changes_dict = self._poll_invalidations()
        if changes_dict is not None:
            processor = getUtility(IInvalidationProcessor)
            d = processor.processQueue(
                tuple(set(self._filter_oids(changes_dict)))
            )

            def done(n):
                if n == INVALIDATIONS_PAUSED:
                    self.sendEvent({
                        'summary': "Invalidation processing is "
                                   "currently paused. To resume, set "
                                   "'dmd.pauseHubNotifications = False'",
                        'severity': SEVERITY_CRITICAL,
                        'eventkey': INVALIDATIONS_PAUSED
                    })
                    self._invalidations_paused = True
                else:
                    msg = 'Processed %s oids' % n
                    self.log.debug(msg)
                    if self._invalidations_paused:
                        self.sendEvent({
                            'summary': msg,
                            'severity': SEVERITY_CLEAR,
                            'eventkey': INVALIDATIONS_PAUSED
                        })
                        self._invalidations_paused = False
            d.addCallback(done)
