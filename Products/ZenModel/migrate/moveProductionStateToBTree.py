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
        
from Acquisition import aq_base
import Migrate

class MoveProductionStateToBTree(Migrate.Step):

    version = Migrate.Version(5,2,0)

    def migrateObject(self, obj):
        obj_unwrapped = aq_base(obj)
        if hasattr(obj_unwrapped, 'productionState'):
            obj._setProductionState(obj_unwrapped.productionState)
            del obj_unwrapped.productionState
        if hasattr(obj_unwrapped, 'preMWProductionState'):
            obj.setPreMWProductionState(obj_unwrapped.preMWProductionState)
            del obj_unwrapped.preMWProductionState

    def cutover(self, dmd):
        for device in dmd.Devices.getSubDevices_recursive():
            self.migrateObject(device)

            # migrate components
            for c in device.getDeviceComponents():
                self.migrateObject(c)

MoveProductionStateToBTree()
