###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__='''
This migration script adds indexes for fields displayed in the
device list.
''' 

__version__ = "$Revision$"[11:-2]
        
from Products.ZCatalog.Catalog import CatalogError
from Products.ZenUtils.Search import makeCaseInsensitiveKeywordIndex
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex

import Migrate

class NewComponentIndexes(Migrate.Step):

    version = Migrate.Version(2, 1, 0)

    def cutover(self, dmd):
        devices = dmd.getDmdRoot('Devices')
        zcat = getattr(devices, 'componentSearch')
        cat = zcat._catalog
        try:
            cat.addIndex('getCollectors', 
                makeCaseInsensitiveKeywordIndex('getCollectors'))
            cat.addIndex('getParentDeviceName', 
                makeCaseInsensitiveFieldIndex('getParentDeviceName'))
            print "Reindexing. This may take some time..."
            zcat.reindexIndex('getCollectors', None)
            zcat.reindexIndex('getParentDeviceName', None)
        except CatalogError:
            pass

NewComponentIndexes()
