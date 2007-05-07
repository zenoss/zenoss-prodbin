###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
"""
MaintenanceWindowable.py

Created by Marc Irlandez on 2007-04-05.
"""
from AccessControl import ClassSecurityInfo
from MaintenanceWindow import MaintenanceWindow
from Products.ZenUtils.Utils import prepId

class MaintenanceWindowable:

    security = ClassSecurityInfo()

    security.declareProtected('Change Device', 'manage_addMaintenanceWindow')
    def manage_addMaintenanceWindow(self, newId=None, REQUEST=None):
        "Add a Maintenance Window to this device"
        mw = None
        if newId:
            preppedId = prepId(newId)
            mw = MaintenanceWindow(preppedId)
            mw.name = newId
            self.maintenanceWindows._setObject(preppedId, mw)
            self.setLastChange() # In Device (not sure if needed by Organizers)
        if REQUEST:
            if mw:
                REQUEST['message'] = "Maintenace Window Added"
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'manage_deleteMaintenanceWindow')
    def manage_deleteMaintenanceWindow(self, maintenanceIds=(), REQUEST=None):
        "Delete a Maintenance Window to this device"
        import types
        if type(maintenanceIds) in types.StringTypes:
            maintenanceIds = [maintenanceIds]
        for id in maintenanceIds:
            self.maintenanceWindows._delObject(id)
        self.setLastChange() # In Device (not sure if needed by Organizers)
        if REQUEST:
            REQUEST['message'] = "Maintenace Window Deleted"
            return self.callZenScreen(REQUEST)


