##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.ZenModel.ZenossSecurity import MANAGER_ROLE, MANAGE_NOTIFICATION_SUBSCRIPTIONS, MANAGE_TRIGGER, NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE, NOTIFICATION_UPDATE_ROLE, NOTIFICATION_VIEW_ROLE, OWNER_ROLE, TRIGGER_MANAGER_ROLE, TRIGGER_UPDATE_ROLE, TRIGGER_VIEW_ROLE, UPDATE_NOTIFICATION, UPDATE_TRIGGER, VIEW_NOTIFICATION, VIEW_TRIGGER, ZEN_ADD, ZEN_ADMINISTRATORS_EDIT, ZEN_ADMINISTRATORS_VIEW, ZEN_ADMIN_DEVICE, ZEN_CHANGE_ADMIN_OBJECTS, ZEN_CHANGE_ALERTING_RULES, ZEN_CHANGE_DEVICE, ZEN_CHANGE_DEVICE_PRODSTATE, ZEN_CHANGE_EVENT_VIEWS, ZEN_CHANGE_SETTINGS, ZEN_COMMON, ZEN_DEFINE_COMMANDS_EDIT, ZEN_DEFINE_COMMANDS_VIEW, ZEN_DELETE, ZEN_DELETE_DEVICE, ZEN_EDIT_LOCAL_TEMPLATES, ZEN_EDIT_USER, ZEN_EDIT_USERGROUP, ZEN_MAINTENANCE_WINDOW_EDIT, ZEN_MAINTENANCE_WINDOW_VIEW, ZEN_MANAGER_ROLE, ZEN_MANAGE_DEVICE, ZEN_MANAGE_DEVICE_STATUS, ZEN_MANAGE_DMD, ZEN_MANAGE_EVENTMANAGER, ZEN_MANAGE_EVENTS, ZEN_RUN_COMMANDS, ZEN_SEND_EVENTS, ZEN_UPDATE, ZEN_USER_ROLE, ZEN_VIEW, ZEN_VIEW_HISTORY, ZEN_VIEW_MODIFICATIONS, ZEN_ZPROPERTIES_EDIT, ZEN_ZPROPERTIES_VIEW
from Products.ZenModel.ServiceClass import ServiceClass


STARTMODE_AUTO = 'Auto'
STARTMODE_MANUAL = 'Manual'
STARTMODE_DISABLED = 'Disabled'
STARTMODE_NOTINSTALLED = 'Not Installed'


class WinServiceClass(ServiceClass):
    """
    Extends ServiceClass to add properties specific to Windows services.
    """

    monitoredStartModes = [STARTMODE_AUTO]

    _properties = ServiceClass._properties + (
        {'id': 'monitoredStartModes', 'type':'lines', 'mode':'rw'},
        )

    factory_type_information = ({
        'id'             : 'WinServiceClass',
        'meta_type'      : 'WinServiceClass',
        'icon'           : 'WinServiceClass.gif',
        'product'        : 'ZenModel',
        'factory'        : 'manage_addWinServiceClass',
        'immediate_view' : 'winServiceClassStatus',
        'actions': (
            { 'id'          : 'status'
            , 'name'        : 'Status'
            , 'action'      : 'winServiceClassStatus'
            , 'permissions' : (ZEN_VIEW,),
            },
            { 'id'          : 'edit'
            , 'name'        : 'Edit'
            , 'action'      : 'winServiceClassEdit'
            , 'permissions' : (ZEN_MANAGE_DMD,),
            },
            { 'id'          : 'manage'
            , 'name'        : 'Administration'
            , 'action'      : 'serviceClassManage'
            , 'permissions' : (ZEN_MANAGE_DMD,)
            },
            { 'id'          : 'zproperties'
            , 'name'        : 'Configuration Properties'
            , 'action'      : 'zPropertyEdit'
            , 'permissions' : (ZEN_CHANGE_DEVICE,)
            },
            ),
        },)

    security = ClassSecurityInfo()


    def manage_editServiceClass(self, name="", monitor=False,
        serviceKeys="", port=0, description="", monitoredStartModes=[],
        REQUEST=None):
        """
        Edit a WinServiceClass.
        """
        if self.monitoredStartModes != monitoredStartModes:
            self.monitoredStartModes = monitoredStartModes
            for inst in self.instances():
                inst._p_changed = True

        return super(WinServiceClass, self).manage_editServiceClass(
            name, monitor, serviceKeys, port, description, REQUEST)


InitializeClass(WinServiceClass)
