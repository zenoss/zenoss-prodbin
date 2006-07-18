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
        ("userSetting", ToOne(ToMany, "UserSettings", "adminRoles")),
        ("device", ToOne(ToManyCont, "UserSettings", "adminRoles")),
    )

    level = 1
    role = "Administrator"


    def deleteAdminRole(self):
        self.device.removeRelation()
        self.userSetting.removeRelation()


    def email(self):
        return self.userSetting().email
  

    def pager(self):
        return self.userSetting().pager

   
    def userLink(self):
        return self.userSetting().getPrimaryUrlPath()


    def deviceName(self):
        return self.device().id


    def deviceLink(self):
        return self.device().getPrimaryUrlPath()


    def deviceClass(self):
        return self.device().getDeviceClassPath()


    def deviceProdState(self):
        return self.device().getProductionStateString()
