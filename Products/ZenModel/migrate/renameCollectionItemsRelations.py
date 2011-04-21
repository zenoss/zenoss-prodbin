###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################


import Migrate
from Acquisition import aq_base
from Products.ZenRelations.ToManyContRelationship import ToManyContRelationship

class renameCollectionItemsRelations(Migrate.Step):
    version = Migrate.Version(3, 0, 0)
    
    def cutover(self, dmd):
        reportclass = dmd.Reports._getOb('Multi-Graph Reports')
        for report in reportclass.reports():

            # if this item does not have a 'collections' attribute
            # go on to the next
            try:
                rptcolls = report.collections
            except AttributeError:
                continue
                
            # for every collection attached to this report,
            # change the 'items' relation to 'collection_items'
            for coll in rptcolls():
                rel = coll.items
                if isinstance(rel, ToManyContRelationship):
                    obs = []
                    for ob in rel():
                        obs.append(aq_base(ob))
                        remote_rel = ob.collection
                        remote_rel._remove(coll)
                        rel._remove(ob)
                    coll._delObject('items')
                    coll.buildRelations()
                    newrel = coll.collection_items.primaryAq()
                    for ob in obs:
                        newrel._setObject(ob.getId(), ob)
                        ob = newrel._getOb(ob.getId())
                        assert ob.__primary_parent__ == newrel
                        assert ob.collection() == coll
                        assert ob in newrel()

renameCollectionItemsRelations()
