#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

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