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

class AdministrativeRoleable:
    
    security = ClassSecurityInfo()

    security.declareProtected('Change Device', 'manage_addAdministrativeRole')
    def manage_addAdministrativeRole(self, newId=None, REQUEST=None):
        "Add a Admin Role to this device"
        us = None
        if newId:
            us = self.ZenUsers.getUserSettings(newId)
        if us:
            ar = AdministrativeRole(newId)
            if us.defaultAdminRole:
                ar.role = us.defaultAdminRole
                ar.level = us.defaultAdminLevel
            self.adminRoles._setObject(newId, ar)
            ar = self.adminRoles._getOb(newId)
            ar.userSetting.addRelation(us)
        if REQUEST:
            if us:
                REQUEST['message'] = "Administrative Role Added"
            return self.callZenScreen(REQUEST)


    def manage_editAdministrativeRoles(self, ids=(), role=(), level=(), REQUEST=None):
        """Edit list of admin roles.
        """
        if type(ids) in types.StringTypes:
            ids = [ids]
            role = [role]
            level = [level]
        for i, id in enumerate(ids):
            ar = self.adminRoles._getOb(id)
            if ar.role != role[i]: ar.role = role[i]
            if ar.level != level[i]: ar.level = level[i]
        if REQUEST:
            REQUEST['message'] = "Administrative Roles Updated"
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device','manage_deleteAdministrativeRole')
    def manage_deleteAdministrativeRole(self, delids=(), REQUEST=None):
        "Delete a admin role to this device"
        if type(delids) in types.StringTypes:
            delids = [delids]
        for id in delids:
            self.adminRoles._delObject(id)
        if REQUEST:
            if delids:
                REQUEST['message'] = "Administrative Roles Deleted"
            return self.callZenScreen(REQUEST)
