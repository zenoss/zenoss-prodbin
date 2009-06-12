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

import Migrate
import logging
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex

log = logging.getLogger( 'zen.migrate' )

def addIndexToCatalog( zCatalog, indexId ):
    if indexId not in zCatalog.indexes():
        cat = zCatalog._catalog
        cat.addIndex( indexId, makeCaseInsensitiveFieldIndex( indexId ) )

class AddTitleOrIdToCatalogs(Migrate.Step):
    version = Migrate.Version(2, 5, 0)

    def cutover(self, dmd):
        zcat = dmd.Devices.deviceSearch
        addIndexToCatalog( zcat, 'titleOrId' )
        log.info( 'Reindexing devices.  This may take a while...' )
        dmd.Devices.reIndex()


AddTitleOrIdToCatalogs()
