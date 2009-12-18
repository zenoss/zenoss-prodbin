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
from Products.Zuul.catalog.global_catalog import createGlobalCatalog
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenRelations.ToManyContRelationship import ToManyContRelationship
from OFS.ObjectManager import ObjectManager
from Products.ZenModel.Device import Device
from Products.ZenModel.RRDTemplate import RRDTemplate

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

            # Use closure so we don't have to traverse to catalog
            # every time
            catalog = zport.global_catalog
            def _catobj(obj):
                catalog.catalog_object(obj)

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

GlobalCatalog()
