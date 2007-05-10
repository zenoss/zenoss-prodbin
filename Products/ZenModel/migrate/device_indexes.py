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
from Products.ZenUtils.Search import makeFieldIndex, makePathIndex

import Migrate

fieldIndexes = ['id', 'getDeviceIp', 'getDeviceClassPath', 'getProdState']
pathIndexes = ['getPhysicalPath']

class NewDeviceIndexes(Migrate.Step):

    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        devices = dmd.getDmdRoot('Devices')
        zcat = getattr(devices, 'deviceSearch')
        cat = zcat._catalog
        reindex = False
        for indexName in fieldIndexes:
            try: 
                cat.getIndex(indexName)
            except KeyError:
                cat.addIndex(indexName, makeFieldIndex(indexName))
                reindex = True
        for indexName in pathIndexes:
            try:
                cat.getIndex(indexName)
            except KeyError:
                cat.addIndex(indexName, makeFieldIndex(indexName))
                reindex = True
        try: 
            cat.addColumn('id')
            reindex = True
        except CatalogError:
            pass
        if reindex: 
            print "Reindexing. This may take some time..."
            devices.reIndex()

NewDeviceIndexes()
