##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Create hooks for finding and displaying maintenance windows
(See ComponentMW ZenPack from services)

'''
import Migrate

from Products.ZenModel.MaintenanceWindow import createMaintenanceWindowCatalog
from Products.ZenUtils.Search import makePathIndex

class MaintenanceWindowHooks(Migrate.Step):
    version = Migrate.Version(5, 0, 0)
    
    def _createNewIndex( mwcat ):
        log.info("Adding new columns to the dmd.maintenanceWindowSearch catalog.")
        mwcat._catalog.addIndex('getPhysicalPath', makePathIndex('getPhysicalPath'))
        mwcat.addColumn('getPhysicalPath')
 
    def _reindexWindows( mwcat ):
        log.info("Re-indexing the dmd.maintenanceWindowSearch catalog....")
        for brain in mwcat():
            obj = brain.getObject()
            obj.reindex_all()
        log.info("Completed re-indexing the dmd.maintenanceWindowSearch catalog!")
    
    def cutover(self, dmd):
        mwcat = dmd.maintenanceWindowSearch
        if 'getPhysicalPath' not in mwcat.indexes():
            _createNewIndex( mwcat )
            _reindexWindows( mwcat )

MaintenanceWindowHooks()
