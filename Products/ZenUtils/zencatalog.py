###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import sys
import logging
from itertools import chain

from Globals import *

import transaction
from twisted.internet import defer, reactor, task
from OFS.ObjectManager import ObjectManager
from ZODB.POSException import ConflictError
from ZEO.Exceptions import ClientDisconnected
from ZEO.zrpc.error import DisconnectedError
from Products.ZenRelations.ToManyContRelationship import ToManyContRelationship
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.Zuul.catalog.global_catalog import createGlobalCatalog

log = logging.getLogger("zen.Catalog")

# Hide connection errors. We handle them all ourselves.
HIGHER_THAN_CRITICAL = 100
logging.getLogger('ZODB.Connection').setLevel(HIGHER_THAN_CRITICAL)
logging.getLogger('ZEO.zrpc').setLevel(HIGHER_THAN_CRITICAL)

CHUNK_SIZE = 100

class DisconnectedDuringGenerator(Exception):
    """
    A special exception that can be yielded during a generator and watched for.
    This lets us react to connection exceptions in the generator without killing it.
    """
    def __init__(self, value):
        self.value = value


def chunk(iterable, callback, reconnect_cb=lambda:None, size=1, delay=1):
    """
    Iterate through a generator, splitting it into chunks of size C{size},
    calling C{callback(chunk)} on each. In case of a
    L{DisconnectedDuringGenerator}, pause for C{delay} seconds, then call
    C{reconnect_cb} and continue with the iteration.

    This is used to walk through the database object by object without dying if
    the database goes away or there's a C{ConflictError}.
    """
    gen = iter(iterable)

    # defer.inlineCallbacks means that Deferreds yielded from the function will
    # execute their callbacks /in order/, blocking each other.
    @defer.inlineCallbacks
    def inner(gen=gen):
        d = defer.Deferred()
        d.addCallback(callback)
        l = []
        while True:
            try:
                # Advance the iterator
                n = gen.next()
            except StopIteration:
                # Iterator's exhausted. Call back with the possibly incomplete
                # chunk, then stop.
                if l:
                    d.callback(l)
                    yield d
                break
            else:
                # We got a value from the iterator
                if isinstance(n, DisconnectedDuringGenerator):
                    # The special exception was yielded, meaning the generator
                    # encountered an exception we want to handle by pausing.
                    # Push the value that broke back onto the front of the
                    # iterator.
                    gen = chain((n.value,), gen)
                    # Yield a C{Deferred} that will call back to
                    # C{reconnect_cb} in C{delay} seconds.  Because we're using
                    # C{inlineCallbacks}, this will block the advance of the
                    # iterator.
                    yield task.deferLater(reactor, delay, reconnect_cb)
                else:
                    # Normal value, add it to the chunk
                    l.append(n)
            # If the chunk is complete, call back the Deferred, yield it, and
            # start a new chunk
            if len(l)==size:
                d.callback(l)
                l = []
                yield d
                d = defer.Deferred()
                d.addCallback(callback)

    # return the C{Deferred} that comes from an C{inlineCallbacks} function.
    return inner()


class ZenCatalog(ZCmdBase):
    name = 'zencatalog'

    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZCmdBase.buildOptions(self)
        self.parser.add_option("--createcatalog",
                               action="store_true",
                               default=False,
                               help="Create global catalog and populate it")
        self.parser.add_option("--forceindex",
                               action="store_true",
                               default=False,
                               help="works with --createcatalog to re-create index, if catalog exists it will be "\
                               "dropped first")
        self.parser.add_option("--reindex",
                               action="store_true",
                               default=False,
                               help="reindex existing catalog")
        self.parser.add_option("--permissionsOnly",
                               action="store_true",
                               default=False,
                               help="Only works with --reindex, only update the permissions catalog")


    def run(self):

        def stop(ignored):
            reactor.stop()

        def main():
            zport = self.dmd.getPhysicalRoot().zport
            if self.options.createcatalog:
                d = self._createCatalog(zport)
            elif self.options.reindex:
                d = self._reindex(zport)
            d.addBoth(stop)

        if not self.options.createcatalog and not self.options.reindex:
            self.parser.error("Must use --createcatalog or --reindex") 
        reactor.callWhenRunning(main)
        reactor.run()

    def _reindex(self, zport):
        globalCat = self._getCatalog(zport)

        if globalCat:
            reindex_catalog(globalCat, self.options.permissionsOnly, not self.options.daemon)
        else:
            log.warning('Global Catalog does not exist, try --createcatalog option')
        return defer.succeed(None)

    def _createCatalog(self, zport):

        # Whether we reconnected after a recursion failure. Because the nested
        # func has no access to this scope, make it a mutable.
        _reconnect = [False]


        catalog = self._getCatalog(zport)
        if self.options.forceindex and catalog:
            zport._delObject(catalog.getId())
            catalog = self._getCatalog(zport)

        if catalog is None:
            # Create the catalog
            log.debug("Creating global catalog")
            createGlobalCatalog(zport)
            catalog = self._getCatalog(zport)
            transaction.commit()
        else:
            log.info('Global catalog already exists. Run with --forceindex to drop and recreate catalog')
            return defer.succeed(None)

        def recurse(obj):
            if _reconnect[0]:
                log.info('Reconnected.')
                _reconnect.pop()
                _reconnect.append(False)
            try:
                if isinstance(obj, ObjectManager):
                    # Bottom up, for multiple-path efficiency
                    for ob in obj.objectValues():
                        for kid in recurse(ob):
                            yield kid
                    if isinstance(obj, ZenModelRM):
                        for rel in obj.getRelationships():
                            if not isinstance(rel, ToManyContRelationship):
                                continue
                            for kid in rel.objectValuesGen():
                                for gkid in recurse(kid):
                                    yield gkid
                        yield obj
            except (AttributeError, ClientDisconnected, DisconnectedError):
                # Yield the special exception C{chunk} is watching for, so
                # it'll pause and wait for a connection. Feed it the current
                # object so it knows where to start from.
                # We'll also catch AttributeErrors, which are thrown when
                # ZenPacks get updated during the run.
                log.info("Connection problem during object retrieval. "
                         "Trying again in 5 seconds...")
                _reconnect.pop()
                _reconnect.append(True)
                yield DisconnectedDuringGenerator(obj)

        def catalog_object(ob):
            if hasattr(ob, 'index_object'):
                ob.index_object()
            catalog.catalog_object(ob)
            log.debug('Catalogued object %s' % ob.absolute_url_path())

        # Count of catalogued objects. Because the nested func has no access to
        # this scope, have to make it a mutable
        i = [0]

        def handle_chunk(c, d=None, _is_reconnect=False):
            """
            Return a Deferred that will call back once the chunk has been
            catalogued. In case of a conflict or disconnect, wait 5 seconds, then
            try again. Because this is a callback chained to a C{chunk} Deferred
            yielded from an C{inlineCallbacks} function, the next chunk will not be
            created until this completes successfully.
            """
            if d is None:
                d = defer.Deferred()
            self.syncdb()
            try:
                for ob in filter(None, c):
                    catalog_object(ob)
                transaction.commit()
            except ConflictError, e:
                log.info('Conflict error during commit. Retrying...')
                log.debug('Object in conflict: %r' % (self.app._p_jar[e.oid],))
                reactor.callLater(0, handle_chunk, c, d)
            except (ClientDisconnected, DisconnectedError):
                log.info('Connection problem during commit. '
                         'Trying again in 5 seconds...')
                reactor.callLater(5, handle_chunk, c, d, True)
            else:
                if _is_reconnect:
                    log.info('Reconnected.')
                d.callback(None)
                # Increment the count
                i.append(i.pop()+len(c))
                if self.options.daemon:
                    log.info("Catalogued %s objects" % i[0])
                else:
                    sys.stdout.write('.')
                    sys.stdout.flush()
            return d

        def reconnect():
            """
            If we had a connection error, the db is probably in a weird state.
            Reset it and try again.
            """
            log.info("Reconnected.")
            self.syncdb()

        def set_flag(r):
            """
            Set a flag in the database saying we've finished indexing.
            """
            if self.options.daemon:
                sys.stdout.write('\n')
            log.debug("Marking the indexing as completed in the database")
            self.syncdb()
            zport._zencatalog_completed = True
            transaction.commit()

        log.info("Reindexing your system. This may take some time.")
        d = chunk(recurse(zport), handle_chunk, reconnect, CHUNK_SIZE, 5)

        return d.addCallbacks(set_flag, log.exception)


    def _getCatalog(self, zport):
        return getattr(zport, 'global_catalog', None)

def reindex_catalog(globalCat, permissionsOnly=False, printProgress=True, commit=True):
    msg = 'objects'
    if permissionsOnly:
        msg = 'permissions'
    log.info('reindexing %s in catalog' % msg)
    i = 0
    catObj = globalCat.catalog_object
    for brain in globalCat():
        log.debug('indexing %s' % brain.getPath())
        try:
            obj = brain.getObject()
        except Exception:
            log.debug("Could not load object: %s" % brain.getPath())
            globalCat.uncatalog_object(brain.getPath())
            continue
        if obj is not None:
            #None defaults to all inedexs
            kwargs = {}
            if permissionsOnly:
                kwargs = {'update_metadata': False,
                          'idxs': ("allowedRolesAndUsers",)}
            elif hasattr(obj, 'index_object'):
                obj.index_object()

            catObj(obj, **kwargs)
            log.debug('Catalogued object %s' % obj.absolute_url_path())
        else:
            log.debug('%s does not exists' % brain.getPath())
            globalCat.uncatalog_object(brain.getPath())
        i += 1
        if not i % CHUNK_SIZE:
            if printProgress:
                sys.stdout.write(".")
                sys.stdout.flush()
            else:
                log.info('Catalogued %s objects' % i)
            if commit:
                transaction.commit()
    if printProgress:
        sys.stdout.write('\n')
        sys.stdout.flush()
    if commit:
        transaction.commit()

if __name__ == "__main__":
    zc = ZenCatalog()
    try:
        zc.run()
    except Exception, e:
        log.exception(e)

