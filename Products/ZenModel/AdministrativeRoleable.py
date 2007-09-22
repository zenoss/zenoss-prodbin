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
AdministrativeRoleable.py

Created by Marc Irlandez on 2007-04-05.
"""

import types
from AccessControl import ClassSecurityInfo
from Products.ZenModel.AdministrativeRole import AdministrativeRole
from Globals import InitializeClass
from ZenossSecurity import *

class AdministrativeRoleable:
    
    security = ClassSecurityInfo()

    security.declareProtected(ZEN_ADMINISTRATORS_VIEW, 
        'getAdministrativeRoles')
    def getAdministrativeRoles(self):
        "Get the Admin Roles on this device"
        return self.adminRoles.objectValuesAll()
        
    security.declareProtected(ZEN_ADMINISTRATORS_EDIT, 
        'manage_addAdministrativeRole')
    def manage_addAdministrativeRole(self, newId=None, REQUEST=None):
        "Add a Admin Role to this device"
        us = self.ZenUsers.getUserSettings(newId)
        AdministrativeRole(us, self)
        self.setAdminLocalRoles()
        if REQUEST:
            if us:
                REQUEST['message'] = "Administrative Role Added"
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_ADMINISTRATORS_EDIT, 
        'manage_editAdministrativeRoles')
    def manage_editAdministrativeRoles(self, ids=(), role=(), 
                                        level=(), REQUEST=None):
        """Edit list of admin roles.
        """
        if type(ids) in types.StringTypes:
            ids = [ids]
            role = [role]
            level = [level]
        for i, id in enumerate(ids):
            ar = self.adminRoles._getOb(id)
            ar.update(role[i], level[i]) 
        self.setAdminLocalRoles()
        if REQUEST:
            REQUEST['message'] = "Administrative Roles Updated"
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_ADMINISTRATORS_EDIT,
        'manage_deleteAdministrativeRole')
    def manage_deleteAdministrativeRole(self, delids=(), REQUEST=None):
        "Delete a admin role to this device"
        if type(delids) in types.StringTypes:
            delids = [delids]
        for userid in delids:
            ar = self.adminRoles._getOb(userid, None)
            if ar is not None: ar.delete()
            self.manage_delLocalRoles((userid,))
        self.setAdminLocalRoles()
        if REQUEST:
            if delids:
                REQUEST['message'] = "Administrative Roles Deleted"
            return self.callZenScreen(REQUEST)

    def manage_listAdministrativeRoles(self):
        """List the user and their roles on an object"""
        return [ (ar.id, (ar.role,)) for ar in self.adminRoles() ]

    
    def setAdminLocalRoles(self):
        """Hook for setting permissions"""
        pass


InitializeClass(AdministrativeRoleable)
