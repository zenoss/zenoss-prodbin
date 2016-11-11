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
import transaction
from Products import Zuul
from Products.Zuul.utils import unbrain
from Products.ZCatalog.Catalog import CatalogError

class MoveProductionStateToBTree(Migrate.Step):

    version = Migrate.Version(107, 0, 0)

    def migrateObject(self, obj):
        obj_unwrapped = aq_base(obj)
        if hasattr(obj_unwrapped, 'productionState'):
            obj._setProductionState(obj_unwrapped.productionState)
            del obj_unwrapped.productionState
        if hasattr(obj_unwrapped, 'preMWProductionState'):
            obj.setPreMWProductionState(obj_unwrapped.preMWProductionState)
            del obj_unwrapped.preMWProductionState

    def cutover(self, dmd):
        # Move production state to BTree
        log.info("Migrating productionState to lookup table")

        # Use device facade to get all devices from the catalog
        facade = Zuul.getFacade('device', dmd)

        # call getDeviceBrains, because getDevices requires ZEP
        brains = facade.getDeviceBrains(limit=None)
        total = brains.total
        count = 1
        devices = (unbrain(b) for b in brains)
        for device in devices:
            if count % 100 == 0:
                log.info("Migrated %d devices of %d", count, total)

            if count % 1000 == 0:
                log.info("Committing transaction for 1000 devices")
                transaction.commit()

            count = count + 1

            self.migrateObject(device)

            # migrate components
            for c in device.getDeviceComponents():
                self.migrateObject(c)

        log.info("All devices migrated")

        # Remove production state from the global and device catalogs
        log.info("Removing production state from catalogs")
        globalCatalog = dmd.getPhysicalRoot().zport.global_catalog
        deviceCatalog = getattr(dmd.Devices, dmd.Devices.default_catalog)

        try: 
            globalCatalog.delIndex('productionState')
        except CatalogError:
            pass

        try:
            deviceCatalog.delIndex('getProdState')
        except CatalogError:
            pass

        log.info("Production state index removed from global and device catalogs")



MoveProductionStateToBTree()
