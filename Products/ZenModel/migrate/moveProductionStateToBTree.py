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
from Products.ZenUtils.productionstate.interfaces import IProdStateManager
from Products.ZCatalog.Catalog import CatalogError

class MoveProductionStateToBTree(Migrate.Step):

    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):
        # Move production state to BTree
        log.info("Migrating productionState to lookup table")

        # Get a production state manager to use for all objects
        mgr = IProdStateManager(dmd)

        # Use device facade to get all devices from the catalog
        facade = Zuul.getFacade('device', dmd)

        # call getDeviceBrains, because getDevices requires ZEP
        brains = facade.getDeviceBrains(limit=None)
        total = brains.total
        devices = (unbrain(b) for b in brains)

        for count, device in enumerate(devices):

            if count and count % 100 == 0:
                log.info("Migrated %d devices of %d", count, total)

            if count and count % 1000 == 0:
                log.info("Committing transaction for %d devices")
                transaction.commit()

            mgr.migrateObject(device)

            # migrate components, if any
            try:
                cmps = device.getDeviceComponents()
            except AttributeError:
                pass
            else:
                for c in cmps:
                    mgr.migrateObject(c)

        # Tidy up whatever's in the last 1000 that didn't get committed
        if count % 100:
            log.info("Migrated %d devices of %d", total, total)
        if count % 1000:
            log.info("Committing transaction for %d devices", count % 1000)
            transaction.commit()

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
