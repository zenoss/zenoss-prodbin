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

from ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *


class AdministrativeRole(ZenModelRM):

    meta_type = "AdministrativeRole"

    _relations = (
        ("userSetting", ToOne(ToMany, "Products.ZenModel.UserSettings", "adminRoles")),
        ("managedObject", ToOne(ToManyCont, "Products.ZenModel.AdministrativeRoleable", "adminRoles")),
    )

    level = 1
    role = "Administrator"


    def deleteAdminRole(self):
        self.managedObject.removeRelation()
        self.userSetting.removeRelation()


    def email(self):
        return self.userSetting().email
  

    def pager(self):
        return self.userSetting().pager

   
    def userLink(self):
        return self.userSetting().getPrimaryUrlPath()


    def managedObjectName(self):
        return self.managedObject().id


    def managedObjectLink(self):
        return self.managedObject().getPrimaryUrlPath()


    def getEventSummary(self):
        return self.managedObject().getEventSummary()


    def managedObjectName(self):
        return self.managedObject().getOrganizerName()