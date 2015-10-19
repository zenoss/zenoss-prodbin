##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """MaintenanceWindowable

Management functions for devices and device classes on their
maintenance windows.

"""

import logging
log = logging.getLogger("zen.MaintenanceWindowable")

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from ZenossSecurity import MANAGER_ROLE, MANAGE_NOTIFICATION_SUBSCRIPTIONS, MANAGE_TRIGGER, NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE, NOTIFICATION_UPDATE_ROLE, NOTIFICATION_VIEW_ROLE, OWNER_ROLE, TRIGGER_MANAGER_ROLE, TRIGGER_UPDATE_ROLE, TRIGGER_VIEW_ROLE, UPDATE_NOTIFICATION, UPDATE_TRIGGER, VIEW_NOTIFICATION, VIEW_TRIGGER, ZEN_ADD, ZEN_ADMINISTRATORS_EDIT, ZEN_ADMINISTRATORS_VIEW, ZEN_ADMIN_DEVICE, ZEN_CHANGE_ADMIN_OBJECTS, ZEN_CHANGE_ALERTING_RULES, ZEN_CHANGE_DEVICE, ZEN_CHANGE_DEVICE_PRODSTATE, ZEN_CHANGE_EVENT_VIEWS, ZEN_CHANGE_SETTINGS, ZEN_COMMON, ZEN_DEFINE_COMMANDS_EDIT, ZEN_DEFINE_COMMANDS_VIEW, ZEN_DELETE, ZEN_DELETE_DEVICE, ZEN_EDIT_LOCAL_TEMPLATES, ZEN_EDIT_USER, ZEN_EDIT_USERGROUP, ZEN_MAINTENANCE_WINDOW_EDIT, ZEN_MAINTENANCE_WINDOW_VIEW, ZEN_MANAGER_ROLE, ZEN_MANAGE_DEVICE, ZEN_MANAGE_DEVICE_STATUS, ZEN_MANAGE_DMD, ZEN_MANAGE_EVENTMANAGER, ZEN_MANAGE_EVENTS, ZEN_RUN_COMMANDS, ZEN_SEND_EVENTS, ZEN_UPDATE, ZEN_USER_ROLE, ZEN_VIEW, ZEN_VIEW_HISTORY, ZEN_VIEW_MODIFICATIONS, ZEN_ZPROPERTIES_EDIT, ZEN_ZPROPERTIES_VIEW
from MaintenanceWindow import MaintenanceWindow
from Products.ZenUtils.Utils import prepId
from Products.ZenWidgets import messaging
from Products.ZenMessaging.audit import audit

class MaintenanceWindowable:

    security = ClassSecurityInfo()

    security.declareProtected(ZEN_MAINTENANCE_WINDOW_VIEW,
        'getMaintenanceWindows')
    def getMaintenanceWindows(self):
        "Get the Maintenance Windows on this device"
        return self.maintenanceWindows.objectValuesAll()
    
    security.declareProtected(ZEN_MAINTENANCE_WINDOW_EDIT, 
        'manage_addMaintenanceWindow')
    def manage_addMaintenanceWindow(self, newId=None, REQUEST=None):
        "Add a Maintenance Window to this device"
        mw = None
        if newId:
            preppedId = prepId(newId)
            mw = MaintenanceWindow(preppedId)
            mw.name = newId
            self.maintenanceWindows._setObject(preppedId, mw)
            if hasattr(self, 'setLastChange'):
                # Only Device and DeviceClass have setLastChange for now.
                self.setLastChange()
        if REQUEST:
            if mw:
                messaging.IMessageSender(self).sendToBrowser(
                    'Window Added',
                    'Maintenance window "%s" has been created.' % mw.name
                )
                audit('UI.MaintenanceWindow.Add', mw)
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MAINTENANCE_WINDOW_EDIT, 
        'manage_deleteMaintenanceWindow')
    def manage_deleteMaintenanceWindow(self, maintenanceIds=(), REQUEST=None):
        "Delete a Maintenance Window to this device"
        if isinstance(maintenanceIds, basestring):
            maintenanceIds = [maintenanceIds]
        for id in maintenanceIds:
            mw = getattr(self.maintenanceWindows, id)
            if mw.started:
                if REQUEST:
                    msg = "Closing and removing maintenance window " \
                          "%s which affects %s" % (
                         mw.displayName(), self.id)
                    log.info(msg)
                    messaging.IMessageSender(self).sendToBrowser(
                        'Window Stopping',
                        msg,
                    )
                mw.end()

            if REQUEST:
                audit('UI.MaintenanceWindow.Delete', mw)
            self.maintenanceWindows._delObject(id)
        if hasattr(self, 'setLastChange'):
            # Only Device and DeviceClass have setLastChange for now.
            self.setLastChange()
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Windows Deleted',
                'Maintenance windows deleted: %s' % ', '.join(maintenanceIds)
            )
            return self.callZenScreen(REQUEST)


InitializeClass(MaintenanceWindowable)
