##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import argparse
import logging

# import sys
import time

from contextlib import closing
from itertools import chain

from ZODB.POSException import POSKeyError

# from ZODB.utils import u64
from zope.component import getGlobalSiteManager, getUtilitiesFor, subscribers
from zope.interface import providedBy

from Products.ZenHub.interfaces import (
    FILTER_EXCLUDE,
    FILTER_INCLUDE,
    IInvalidationFilter,
    IInvalidationOid,
    # IInvalidationProcessor,
)
from Products.ZenHub.zodb import UpdateEvent, DeletionEvent
from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.ZenRelations.PrimaryPathObjectManager import (
    PrimaryPathObjectManager,
)
from Products.ZenossApp.db import getDB
from Products.ZenossApp.zodb import dataroot

# from Products.ZenHub.invalidationmanager import InvalidationManager

log = logging.getLogger("zen")
log.setLevel(logging.INFO)

logging.getLogger("txn").setLevel(logging.WARN)
logging.getLogger("relstorage").setLevel(logging.WARN)
logging.getLogger("urllib3").setLevel(logging.WARN)
logging.getLogger("zen.modelindex").setLevel(logging.WARN)


def sendEvent(*args):
    print(args)


def load_invalidation_filters(dmd):
    """Get Invalidation Filters, initialize them,
    store them in the _invalidation_filters list, and return the list
    """
    try:
        filters = (f for n, f in getUtilitiesFor(IInvalidationFilter))
        invalidation_filters = []
        for fltr in sorted(filters, key=lambda f: getattr(f, "weight", 100)):
            fltr.initialize(dmd)
            invalidation_filters.append(fltr)
        log.info(
            "Registered %s invalidation filters.",
            len(invalidation_filters),
        )
        log.info("invalidation filters: %s", invalidation_filters)
        return invalidation_filters
    except Exception:
        log.exception("error in initialize_invalidation_filters")
        return []


class Sink(Exception):
    def __init__(self, oid):
        self.oid = oid


class Skip(Exception):
    def __init__(self, oid):
        self.oid = oid


def oid_to_obj(app, oid):
    # Include oids that are missing from the database
    try:
        obj = app._p_jar[oid]
    except POSKeyError:
        raise Sink(oid)

    # Exclude any unmatched types
    if not isinstance(obj, (PrimaryPathObjectManager, DeviceComponent)):
        raise Skip(oid)

    # Include deleted oids
    try:
        obj = obj.__of__(app.zport.dmd).primaryAq()
    except (AttributeError, KeyError):
        raise Sink(oid)

    return (oid, obj)


def filter_obj(filters, oid, obj):
    included = True
    for fltr in filters:
        result = fltr.include(obj)
        if result is FILTER_INCLUDE:
            log.info("filter %s INCLUDE %r:%r", fltr, oid, obj)
            break
        if result is FILTER_EXCLUDE:
            log.info("filter %s EXCLUDE %r:%r", fltr, oid, obj)
            included = False
            break
    if included:
        log.info("filters FALLTHROUGH: %r", obj)
        return (oid, obj)
        # target.send((oid, obj))

    log.info("Ignored (filtered out): %r", obj)
    raise Skip(oid)


def transform_obj(oid, obj):
    # First, get any subscription adapters registered as transforms
    adapters = subscribers((obj,), IInvalidationOid)
    # Next check for an old-style (regular adapter) transform
    try:
        adapters = chain(adapters, (IInvalidationOid(obj),))
    except TypeError:
        # No old-style adapter is registered
        pass
    transformed = set()

    adapters = list(adapters)
    if adapters:
        log.info(
            "Found %d IInvalidationOid adapters for %s", len(adapters), obj
        )
    else:
        log.info("No IInvalidationOid adapters")

    for adapter in adapters:
        o = adapter.transformOid(oid)
        log.info("adapter %s returned %r for %r", adapter, o, oid)
        if isinstance(o, str):
            transformed.add(o)
        elif hasattr(o, "__iter__"):
            # If the transform didn't give back a string, it should have
            # given back an iterable
            transformed.update(o)
    # Get rid of any useless Nones
    transformed.discard(None)
    # Get rid of the original oid, if returned. We don't want to use it IF
    # any transformed oid came back.
    transformed.discard(oid)
    return transformed or (oid,)


def send_event(event):
    gsm = getGlobalSiteManager()
    sub1 = gsm.adapters.subscriptions(providedBy(event.object), None)
    sub2 = gsm.adapters.subscriptions(providedBy(event), None)
    log.info("%s", sub1)
    log.info("%s", sub2)
    # subscriptions = gsm.adapters.subscriptions(
    #     map(providedBy, (event.object, event)), None
    # )
    # for subscription in subscriptions:
    #     yield giveTimeToReactor(subscription, event.object, event)
    # log.info("%s", subscribers((event.object,), providedBy(event.object)))
    # log.info("%s", subscribers((event,), providedBy(event)))


def handle_oid(dmd, oid):
    # Go pull the object out of the database
    obj = dmd._p_jar[oid]
    # Don't bother with all the catalog stuff; we're depending on primaryAq
    # existing anyway, so only deal with it if it actually has primaryAq.
    if isinstance(obj, (PrimaryPathObjectManager, DeviceComponent)):
        try:
            # Try to get the object
            obj = obj.__of__(dmd).primaryAq()
        except (AttributeError, KeyError):
            # Object has been removed from its primary path (i.e. was
            # deleted), so make a DeletionEvent
            log.debug("Notifying services that %r has been deleted", obj)
            event = DeletionEvent(obj, oid)
        else:
            # Object was updated, so make an UpdateEvent
            log.debug("Notifying services that %r has been updated", obj)
            event = UpdateEvent(obj, oid)
        # Fire the event for all interested services to pick up
        # adapters = subscribers((obj,), IInvalidationOid)
        send_event(event)
        return event


def app(args):
    log.info("Beginning app")
    with closing(getDB(args.zodb_config_file)) as db:
        with closing(db.open()) as session:
            with dataroot(session) as dmd:
                filters = load_invalidation_filters(dmd)
                root = dmd.getPhysicalRoot()
                log.info("Monitoring invalidations")
                while True:
                    session.sync()
                    raw_oids = db.storage.poll_invalidations() or set()
                    processed_oids = set()
                    for oid in raw_oids:
                        oids = work(oid, filters, root)
                        if oids:
                            processed_oids.update(oids)
                    log.info("processed oids: %s", processed_oids)
                    for oid in processed_oids:
                        # ioid = u64(oid)
                        event = handle_oid(dmd, oid)
                        log.info(
                            "%s: %s %r",
                            type(event).__name__,
                            event.object,
                            event.oid,
                        )

                    time.sleep(5)


def work(oid, filters, app):
    log.info("Processing oid %r", oid)
    try:
        oid, obj = oid_to_obj(app, oid)
        oid, obj = filter_obj(filters, oid, obj)
        return transform_obj(oid, obj)
    except Skip as e:
        log.info("Ignoring %r", e.oid)
    except Sink as e:
        return (e.oid,)


def _build_cli_args():
    parser = argparse.ArgumentParser(
        description="Alias Manager for Analytics",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--zodb-config-file",
        default="/opt/zenoss/etc/zodb.conf",
        help="ZODB connection config file.  If the file doesn't exist, "
        "the ZODB connection is created using /opt/zenoss/etc/globals.conf",
    )
    parser.set_defaults(func=app)
    return parser


def main():
    parser = _build_cli_args()
    args = parser.parse_args()
    args.func(args)
