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
__doc__='''
This migration script adds additional indexes and metadata to the existing
productSearch catalog. It is primarily intended to speed up the performance of
a device's Edit tab on systems with a large number of products.
''' 

__version__ = "$Revision$"[11:-2]
        
from Products.ZCatalog.Catalog import CatalogError
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex
from Products.ManagableIndex import FieldIndex

import Migrate

class NewProductIndexes(Migrate.Step):

    version = Migrate.Version(2, 4, 0)

    def cutover(self, dmd):
        manufacturers = dmd.getDmdRoot('Manufacturers')
        zcat = manufacturers.productSearch
        cat = zcat._catalog
        try:
            cat.addIndex('getManufacturerName',
                makeCaseInsensitiveFieldIndex('getManufacturerName'))
            cat.addIndex('meta_type',
                makeCaseInsensitiveFieldIndex('meta_type'))
            cat.addIndex('isOS', FieldIndex('isOS'))

            zcat.addColumn('id')

            print "Reindexing products. This may take some time..."
            manufacturers.reIndex()
        except CatalogError:
            pass

NewProductIndexes()
