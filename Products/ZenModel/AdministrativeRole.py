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


    def getAdminRoles(self):
        """Return list of role names.
        """

    def email(self):
        return self.userSetting().email
  

    def pager(self):
        return self.userSetting().pager

   
    def userLink(self):
        return self.userSetting().getPrimaryUrlPath()
