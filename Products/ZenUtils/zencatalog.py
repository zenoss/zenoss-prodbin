###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import sys
import logging

from Globals import *

from OFS.ObjectManager import ObjectManager
from ZODB.POSException import ConflictError
from Products.ZenRelations.ToManyContRelationship import ToManyContRelationship
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.Device import Device
from Products.ZenModel.RRDTemplate import RRDTemplate
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.Zuul.catalog.global_catalog import createGlobalCatalog

log = logging.getLogger("zen.catalog")

CHUNK_SIZE = 100

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
                               help="works with --createcatalog to create index"\
                               " even if catalog exists")
        self.parser.add_option("--reindex",
                               action="store_true",
                               default=False,
                               help="reindex existing catalog")

    def run(self):
        zport = self.dmd.getPhysicalRoot().zport
        
        if self.options.createcatalog:
            self._createCatalog(zport)
        elif self.options.reindex:
            self._reindex(zport)
            

    def _reindex(self, zport):
        globalCat = self._getCatalog(zport)
        
        if globalCat:
            log.info('reindexing objects in catalog')
            i = 0
            catObj = globalCat.catalog_object
            for brain in globalCat():
                log.debug('indexing %s' % brain.getPath())
                obj = brain.getObject()
                if obj is not None:
                    self._catObj(catObj, obj, i)
                else:
                    log.debug('%s does not exists' % brain.getPath())
                    #TODO uncatalog object
                i += 1
            
            import transaction
            transaction.commit()
            self._logIndexed(i)
        else:
            log.warning('Global Catalog does not exist, try --createcatalog option')

    def _createCatalog(self, zport):
        catalogExists = self._getCatalog(zport)
        if not catalogExists:
            # Create the catalog
            createGlobalCatalog(zport)
        else:
            log.info('Global catalog already exists')

        if not catalogExists or self.options.forceindex:
            self._queuesize = 0
            self._queue = []
            self._tempqueue = []
            # And now, the fun part: index every ZenModelRM
            log.info("Reindexing your system. This may take some time.")
            i = 0
            # Find every object
            globalCat = self._getCatalog(zport)
            catObj = globalCat.catalog_object
            for ob in self._recurse(zport):
                i = self._catObj(catObj, ob, i)
            while self._queue:
                ob = self._queue.pop()
                i = self._catObj(catObj, ob, i)
            import transaction
            transaction.commit()
            self._logIndexed(i)
            log.info("Create Catalog complete")

    def _logIndexed(self, i):
        if self.options.daemon:
            log.info('%s objects indexed' % i)
            queuesize = len(self._queue)
            if queuesize!=self._queuesize:
                log.info('%s objects in retry queue' % queuesize)
                self._queuesize = queuesize

    def _getCatalog(self, zport):
        return getattr(zport, 'global_catalog', None)

    def _catObj(self, catObj, obj, i):
        try:
            self._tempqueue.append(obj)
            catObj(obj)
            # Reindex the old catalogs for device and template
            if isinstance(obj, (Device, RRDTemplate)):
                obj.index_object()
            if not i % CHUNK_SIZE:
                if not self.options.daemon:
                    sys.stdout.write('.')
                    sys.stdout.flush()
                import transaction
                transaction.commit()
                self.syncdb()
                self._logIndexed(i)
                self._tempqueue = []
        except ConflictError:
            self._queue.extend(self._tempqueue)
            self._tempqueue = []
            self.syncdb()
            i -= CHUNK_SIZE
        except:
            log.error('cataloging object at %s failed' % 
                      obj.getPrimaryUrlPath(), exc_info=sys.exc_info())
        else:
            i += 1
        return i

    def _recurse(self, obj):
        if isinstance(obj, ObjectManager):
            # Bottom up, for multiple-path efficiency
            for ob in obj.objectValues():
                for kid in self._recurse(ob):
                    yield kid
            if isinstance(obj, ZenModelRM):
                for rel in obj.getRelationships():
                    if not isinstance(rel, ToManyContRelationship):
                        continue
                    for kid in rel.objectValuesGen():
                        for gkid in self._recurse(kid):
                            yield gkid
                yield obj

if __name__ == "__main__":
    zc = ZenCatalog()
    try:
        zc.run()
    except Exception, e:
        log.exception(e)

