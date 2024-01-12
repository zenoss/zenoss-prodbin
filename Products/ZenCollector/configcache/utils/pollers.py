##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging

from itertools import chain

from zope.component import getUtilitiesFor

from Products.ZenHub.interfaces import IInvalidationFilter

from ..modelchange import InvalidationProcessor

log = logging.getLogger("zen.configcache")


class RelStorageInvalidationPoller(object):
    """
    Wraps a :class:`relstorage.storage.RelStorage` object to provide an
    API to return the latest database invalidations.
    """

    def __init__(self, storage, session, dmd):
        """
        Initialize a RelStorageInvalidationPoller instance.

        :param storage: relstorage storage object
        :type storage: :class:`relstorage.storage.RelStorage`
        """
        self.__storage = storage
        self.__session = session
        app = dmd.getPhysicalRoot()
        filters = initialize_invalidation_filters(dmd)
        self.__processor = InvalidationProcessor(app, filters)

    def poll(self):
        """
        Return an iterable of ZODB objects that have changed since the last
        time `poll` was called.

        :rtype: Iterable[ZODB object]
        """
        self.__session.sync()
        oids = self.__storage.poll_invalidations()
        if not oids:
            return ()
        return set(
            chain.from_iterable(self.__processor.apply(oid) for oid in oids)
        )


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
            "registered %s invalidation filters.", len(invalidation_filters)
        )
        if log.isEnabledFor(logging.DEBUG):
            log.debug(
                "invalidation filters: %s",
                ", ".join(
                    "{0.__module__}.{0.__class__.__name__}".format(flt)
                    for flt in invalidation_filters
                )
            )
        return invalidation_filters
    except Exception:
        log.exception("error in initialize_invalidation_filters")
