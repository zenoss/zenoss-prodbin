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
from Products.ZenModel.ZenossSecurity import *

class ChangeDeviceProdStatePermission(Migrate.Step):
    """
    The ZEN_CHANGE_DEVICE_PRODSTATE (Change Device Production State) permission
    has been added to Zenoss 2.5. This migrate script is used to update the
    appropriate menu item permissions for upgraded systems.
    """

    version = Migrate.Version(2, 5, 0)

    def cutover(self, dmd):
        zport = dmd.zport
        if ZEN_CHANGE_DEVICE_PRODSTATE not in zport.possible_permissions():
            zport.__ac_permissions__ = (
                zport.__ac_permissions__ + ((ZEN_CHANGE_DEVICE_PRODSTATE, (),
                    [ZEN_MANAGER_ROLE, OWNER_ROLE, MANAGER_ROLE]),))

        m = dmd.zenMenus
        m.Device_list.zenMenuItems.setProductionState.permissions = \
                (ZEN_CHANGE_DEVICE_PRODSTATE,)
        m.DeviceGrid_list.zenMenuItems.setProductionState_grid.permissions = \
                (ZEN_CHANGE_DEVICE_PRODSTATE,)
        m.Edit.zenMenuItems.setProductionState.permissions = \
                (ZEN_CHANGE_DEVICE_PRODSTATE,)


changeDeviceProdStatePermission = ChangeDeviceProdStatePermission()
