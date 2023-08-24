##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging

from itertools import chain

from twisted.internet.defer import inlineCallbacks
from zenoss.protocols.protobufs.zep_pb2 import (
    SEVERITY_CLEAR,
    SEVERITY_CRITICAL,
)
from zope.component import getUtility, getUtilitiesFor

from .interfaces import IInvalidationFilter, IInvalidationProcessor
from .handlers import INVALIDATIONS_PAUSED
from .processor import InvalidationProcessor

log = logging.getLogger("zen.{}".format(__name__.split(".")[-1].lower()))


def initialize_invalidation_filters(ctx):
    """
    Return initialized IInvalidationFilter objects in a list.

    :param ctx: Used to initialize the IInvalidationFilter objects.
    :type ctx: DataRoot
    :return: Initialized IInvalidationFilter objects
    :rtype: List[IInvalidationFilter]
    """
    try:
        filters = (f for n, f in getUtilitiesFor(IInvalidationFilter))
        invalidation_filters = []
        for fltr in sorted(filters, key=lambda f: getattr(f, "weight", 100)):
            fltr.initialize(ctx)
            invalidation_filters.append(fltr)
        log.info(
            "Registered %s invalidation filters.",
            len(invalidation_filters),
        )
        log.info("invalidation filters: %s", invalidation_filters)
        return invalidation_filters
    except Exception:
        log.exception("error in initialize_invalidation_filters")


class InvalidationManager(object):

    _invalidation_paused_event = {
        "summary": (
            "Invalidation processing is currently paused. To resume, "
            "set 'dmd.pauseHubNotifications = False'"
        ),
        "severity": SEVERITY_CRITICAL,
        "eventkey": INVALIDATIONS_PAUSED,
    }

    _invalidation_unpaused_event = {
        "summary": "Invalidation processing unpaused",
        "severity": SEVERITY_CLEAR,
        "eventkey": INVALIDATIONS_PAUSED,
    }

    def __init__(self, dmd, poller, interval=30):
        self.__dmd = dmd
        self.__poller = poller
        self._interval = interval
        app = self.__dmd.getPhysicalRoot()
        filters = initialize_invalidation_filters(dmd)
        self.__processor = InvalidationProcessor(app, filters)

    def poll(self):
        """
        Return a set of ZODB objects that have changed since the last
        time `poll` was called.

        :rtype: Set[ZODB object]
        """
        try:
            oids = self.__poller.poll()
            if not oids:
                log.debug("no invalidations found")
                return

            try:
                return set(
                    chain.from_iterable(
                        self.__processor.get(oid) for oid in oids
                    )
                )
            finally:
                log.debug("Processed %s raw invalidations", len(oids))
        # except Exception:
        #     log.exception("error in process_invalidations")
        finally:
            log.debug("end process_invalidations")

    def _paused(self):
        if not self._currently_paused:
            if self.__dmd.pauseHubNotifications:
                self._currently_paused = True
                log.info("invalidation processing has been paused")
                self._send_event(self._invalidation_paused_event)
                return True
            else:
                return False

        else:
            if self.__dmd.pauseHubNotifications:
                log.debug("invalidation processing is paused")
                return True
            else:
                self._currently_paused = False
                log.info("invalidation processing has been unpaused")
                self._send_event(self._invalidation_unpaused_event)
                return False

    @inlineCallbacks
    def _send_event(self, event):
        yield self.__send_event(event)
