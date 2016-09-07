##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''
This migration script moves production state for all devices and components into the new BTree.
''' 

__version__ = "$Revision$"[11:-2]

import logging
log = logging.getLogger("zen.migrate")
from Acquisition import aq_base
import Migrate

class MoveProductionStateToBTree(Migrate.Step):

    version = Migrate.Version(5,2,0)

    def migrateObject(self, obj):
        obj_unwrapped = aq_base(obj)
        migrated=False
        if hasattr(obj_unwrapped, 'productionState'):
            obj._setProductionState(obj_unwrapped.productionState)
            del obj_unwrapped.productionState
            migrated=True
        if hasattr(obj_unwrapped, 'preMWProductionState'):
            obj.setPreMWProductionState(obj_unwrapped.preMWProductionState)
            del obj_unwrapped.preMWProductionState
            migrated=True
        return migrated

    def cutover(self, dmd):
        log.info("Migrating productionState to lookup table")
        total=len(dmd.Devices.getSubDevices_recursive())
        count = 1
        for device in dmd.Devices.getSubDevices_recursive():
            log.info("Checking if productionState migration required for device %d of %d (%s)", count, total, device)
            migrated = self.migrateObject(device)

            # migrate components
            for c in device.getDeviceComponents():
                cMigrated = self.migrateObject(c)
                migrated = migrated or cMigrated

            if migrated:
                log.info("Successfully migrated productionState for %s", device)

        log.info("All devices migrated")

MoveProductionStateToBTree()
