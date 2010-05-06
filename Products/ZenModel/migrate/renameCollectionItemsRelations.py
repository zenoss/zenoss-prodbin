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


import Migrate
from Products.ZenRelations.ToManyContRelationship import ToManyContRelationship

class renameCollectionItemsRelations(Migrate.Step):
    version = Migrate.Version(2, 6, 0)
    
    def cutover(self, dmd):
        reportclass = dmd.Reports._getOb('Multi-Graph Reports')
        for report in reportclass.reports():
            for coll in report.collections():
                rel = coll.items
                if isinstance(rel, ToManyContRelationship):
                    coll._delObject('items')
                    coll._setObject('collection_items', rel)

renameCollectionItemsRelations()
