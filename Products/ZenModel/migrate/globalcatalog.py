###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import sys
import Migrate
from Products.ZCatalog.Catalog import CatalogError
from Products.Zuul.catalog.global_catalog import createGlobalCatalog
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenRelations.ToManyContRelationship import ToManyContRelationship
from OFS.ObjectManager import ObjectManager
from Products.ZenModel.Device import Device
from Products.ZenModel.RRDTemplate import RRDTemplate
from Products.ZenUtils.Search import makeCaseSensitiveFieldIndex

def recurse(obj):
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


class GlobalCatalog(Migrate.Step):
    version = Migrate.Version(2, 6, 0)

    def __init__(self):
        Migrate.Step.__init__(self)
        import reindexdevices
        self.dependencies = [reindexdevices.upgradeindices]

    def cutover(self, dmd):
        zport = dmd.getPhysicalRoot().zport

        if getattr(zport, 'global_catalog', None) is None:

            # Create the catalog
            createGlobalCatalog(zport)


            # And now, the fun part: index every ZenModelRM

            # Get reference to method so we don't have to traverse to catalog
            # every time
            _catobj = zport.global_catalog.catalog_object

            print "Reindexing your system. This may take some time."
            i=0
            # Find every object
            for ob in recurse(zport):
                _catobj(ob)
                # Reindex the old catalogs for device and template
                if isinstance(ob, (Device,RRDTemplate)):
                    ob.index_object()
                if not i%100:
                    sys.stdout.write('.')
                    sys.stdout.flush()
                i+=1
            print

        # Add the ipAddress and/or uid indices if you already have a catalog
        else:
            indices = zport.global_catalog.indexes()
            toreindex = []
            cat = zport.global_catalog._catalog
            newColumn = False
            
            if 'uid' not in indices:
                cat.addIndex('uid', makeCaseSensitiveFieldIndex('uid'))
                toreindex.append('uid')

            if 'ipAddress' not in indices:
                cat.addIndex('ipAddress',
                             makeCaseSensitiveFieldIndex('ipAddress'))
                toreindex.append('ipAddress')

            # attempt to add the column if it does not exist
            try:
                cat.addColumn('zProperties')
                newColumn = True
            except CatalogError:
                # column already exists
                pass
            
            # if we have a new column or new indexes we should re-catalog
            # everything so that all the indexes/meta-data is up to date
            if toreindex or newColumn:
                print ("Reindexing the Catalog. "
                       "Patience is a virtue.")
                i=0
                _catobj = zport.global_catalog.catalog_object
                for b in zport.global_catalog():
                    # if we added an index, reindex the object, if we added a column
                    # update the metadata
                    _catobj(b.getObject(), idxs=toreindex, update_metadata=newColumn)
                    if not i%100:
                        sys.stdout.write('.')
                        sys.stdout.flush()
                    i+=1
                print





GlobalCatalog()
