##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import Migrate
import logging
from Products.ZenModel.ZenossSecurity import (
    MANAGER_ROLE, MANAGE_NOTIFICATION_SUBSCRIPTIONS, MANAGE_TRIGGER,
    NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE, NOTIFICATION_UPDATE_ROLE,
    NOTIFICATION_VIEW_ROLE, OWNER_ROLE, TRIGGER_MANAGER_ROLE,
    TRIGGER_UPDATE_ROLE, TRIGGER_VIEW_ROLE, UPDATE_NOTIFICATION,
    UPDATE_TRIGGER, VIEW_NOTIFICATION, VIEW_TRIGGER, ZEN_ADD,
    ZEN_ADMINISTRATORS_EDIT, ZEN_ADMINISTRATORS_VIEW, ZEN_ADMIN_DEVICE,
    ZEN_CHANGE_ADMIN_OBJECTS, ZEN_CHANGE_ALERTING_RULES, ZEN_CHANGE_DEVICE,
    ZEN_CHANGE_DEVICE_PRODSTATE, ZEN_CHANGE_EVENT_VIEWS, ZEN_CHANGE_SETTINGS,
    ZEN_COMMON, ZEN_DEFINE_COMMANDS_EDIT, ZEN_DEFINE_COMMANDS_VIEW, ZEN_DELETE,
    ZEN_DELETE_DEVICE, ZEN_EDIT_LOCAL_TEMPLATES, ZEN_EDIT_USER,
    ZEN_EDIT_USERGROUP, ZEN_MAINTENANCE_WINDOW_EDIT,
    ZEN_MAINTENANCE_WINDOW_VIEW, ZEN_MANAGER_ROLE, ZEN_MANAGE_DEVICE,
    ZEN_MANAGE_DEVICE_STATUS, ZEN_MANAGE_DMD, ZEN_MANAGE_EVENTMANAGER,
    ZEN_MANAGE_EVENTS, ZEN_RUN_COMMANDS, ZEN_SEND_EVENTS, ZEN_UPDATE,
    ZEN_USER_ROLE, ZEN_VIEW, ZEN_VIEW_HISTORY, ZEN_VIEW_MODIFICATIONS,
    ZEN_ZPROPERTIES_EDIT, ZEN_ZPROPERTIES_VIEW)


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
