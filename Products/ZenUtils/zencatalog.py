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

class ZenCatalog(ZCmdBase):
    name = 'zencatalog'

    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZCmdBase.buildOptions(self)
        self.parser.add_option("--createcatalog",
                               action="store_true",
                               default=False,
                               help="Create global catalog and populate it")
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
                i += 1
            
            import transaction
            transaction.commit()
        else:
            log.warning('Global Catalog does not exist, try --createcatalog option')

    def _createCatalog(self, zport):
        if self._getCatalog(zport) is None:
            # Create the catalog
            createGlobalCatalog(zport)
            # And now, the fun part: index every ZenModelRM
            log.info("Reindexing your system. This may take some time.")
            i = 0
            # Find every object
            globalCat = self._getCatalog(zport)
            catObj = globalCat.catalog_object
            for ob in self._recurse(zport):
                self._catObj(catObj, ob, i)
                i += 1
            import transaction
            transaction.commit()
            log.info("Create Catalog complete")
        else:
            log.info('Global catalog already exists')

    def _getCatalog(self, zport):
        return getattr(zport, 'global_catalog', None)
        
    def _catObj(self, catObj, obj, i):
        try:
            catObj(obj)
            # Reindex the old catalogs for device and template
            if isinstance(obj, (Device, RRDTemplate)):
                obj.index_object()
            if not i % 100:
                if self.options.daemon:
                    log.info('%s objects indexed' % i)
                else:
                    sys.stdout.write('.')
                    sys.stdout.flush()
                import transaction
                transaction.commit()
        except ConflictError:
            raise
        except:
            log.error('cataloging object at %s failed' % 
                      obj.getPrimaryUrlPath(), exc_info=sys.exc_info())

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
    zc.run()

