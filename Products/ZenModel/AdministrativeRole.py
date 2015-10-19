##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenRelations.RelSchema import RELMETATYPES, RelSchema, ToMany, ToManyCont, ToOne
from ZenModelRM import ZenModelRM
from ZenossSecurity import MANAGER_ROLE, MANAGE_NOTIFICATION_SUBSCRIPTIONS, MANAGE_TRIGGER, NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE, NOTIFICATION_UPDATE_ROLE, NOTIFICATION_VIEW_ROLE, OWNER_ROLE, TRIGGER_MANAGER_ROLE, TRIGGER_UPDATE_ROLE, TRIGGER_VIEW_ROLE, UPDATE_NOTIFICATION, UPDATE_TRIGGER, VIEW_NOTIFICATION, VIEW_TRIGGER, ZEN_ADD, ZEN_ADMINISTRATORS_EDIT, ZEN_ADMINISTRATORS_VIEW, ZEN_ADMIN_DEVICE, ZEN_CHANGE_ADMIN_OBJECTS, ZEN_CHANGE_ALERTING_RULES, ZEN_CHANGE_DEVICE, ZEN_CHANGE_DEVICE_PRODSTATE, ZEN_CHANGE_EVENT_VIEWS, ZEN_CHANGE_SETTINGS, ZEN_COMMON, ZEN_DEFINE_COMMANDS_EDIT, ZEN_DEFINE_COMMANDS_VIEW, ZEN_DELETE, ZEN_DELETE_DEVICE, ZEN_EDIT_LOCAL_TEMPLATES, ZEN_EDIT_USER, ZEN_EDIT_USERGROUP, ZEN_MAINTENANCE_WINDOW_EDIT, ZEN_MAINTENANCE_WINDOW_VIEW, ZEN_MANAGER_ROLE, ZEN_MANAGE_DEVICE, ZEN_MANAGE_DEVICE_STATUS, ZEN_MANAGE_DMD, ZEN_MANAGE_EVENTMANAGER, ZEN_MANAGE_EVENTS, ZEN_RUN_COMMANDS, ZEN_SEND_EVENTS, ZEN_UPDATE, ZEN_USER_ROLE, ZEN_VIEW, ZEN_VIEW_HISTORY, ZEN_VIEW_MODIFICATIONS, ZEN_ZPROPERTIES_EDIT, ZEN_ZPROPERTIES_VIEW


class AdministrativeRole(ZenModelRM):

    meta_type = "AdministrativeRole"

    _relations = (
        ("userSetting", ToOne(ToMany, "Products.ZenModel.UserSettings", "adminRoles")),
        ("managedObject", ToOne(ToManyCont, "Products.ZenModel.AdministrativeRoleable", "adminRoles")),
    )

    role = ZEN_USER_ROLE

    def __init__(self, userSettings, managedObject):
        userid = userSettings.getId()
        ZenModelRM.__init__(self, userid)
        self.role = userSettings.defaultAdminRole
        self.id = userid
        managedObject = managedObject.primaryAq()
        managedObject.adminRoles._setObject(userid, self)
        self.userSetting.addRelation(userSettings)
        managedObject.manage_setLocalRoles(userid, (self.role,),)
        managedObject.index_object()


    def update(self, role):
        self.role = role
        managedObject = self.managedObject().primaryAq()
        managedObject.manage_setLocalRoles(self.getId(), (self.role,))
        managedObject.index_object()


    def delete(self):
        managedObject = self.managedObject().primaryAq()
        managedObject.manage_delLocalRoles((self.getId(),))
        managedObject.index_object()
        self.userSetting.removeRelation()
        self.managedObject.removeRelation()


    def email(self):
        return self.userSetting().email
  

    def pager(self):
        return self.userSetting().pager

   
    def userLink(self):
        return self.userSetting().getPrimaryUrlPath()

    def managedObjectName(self):
        from Device import Device
        mo = self.managedObject()
        if isinstance(mo, Device) or mo.meta_type == 'Device':
            return mo.id
        return mo.getOrganizerName()

    def getEventSummary(self):
        return self.managedObject().getEventSummary()
    
    def managedObjectType(self):
        return self.managedObject().meta_type

DeviceAdministrativeRole = AdministrativeRole
DevOrgAdministrativeRole = AdministrativeRole
