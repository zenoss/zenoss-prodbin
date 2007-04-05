"""
MaintenanceWindowable.py

Created by Marc Irlandez on 2007-04-05.
"""
from AccessControl import ClassSecurityInfo

class MaintenanceWindowable:

    security = ClassSecurityInfo()

    security.declareProtected('Change Device', 'manage_addMaintenanceWindow')
    def manage_addMaintenanceWindow(self, newId=None, REQUEST=None):
        "Add a Maintenance Window to this device"
        mw = None
        if newId:
            mw = MaintenanceWindow(newId)
            self.maintenanceWindows._setObject(newId, mw)
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


