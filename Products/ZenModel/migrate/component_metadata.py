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
This migration script adds meta_type metadata to the component catalog
''' 

__version__ = "$Revision$"[11:-2]
        
from Products.ZCatalog.Catalog import CatalogError

import Migrate

class NewComponentMetadata(Migrate.Step):

    version = Migrate.Version(2, 1, 0)

    def cutover(self, dmd):
        devices = dmd.getDmdRoot('Devices')
        zcat = devices.componentSearch
        cat = zcat._catalog
        reindex = False
        try: 
            cat.addColumn('meta_type')
            reindex = True
        except CatalogError:
            pass
        if reindex: 
            print "Reindexing. This may take some time..."
            devices.reIndex()

NewComponentMetadata()
