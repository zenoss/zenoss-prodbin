##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""PowerSupply

PowerSupply is an abstraction of a power supply on a device.

$Id: PowerSupply.py,v 1.7 2004/04/06 22:33:24 edahl Exp $"""

__version__ = "$Revision: 1.7 $"[11:-2]

from Globals import InitializeClass

from Products.ZenRelations.RelSchema import (
    RELMETATYPES, RelSchema, ToMany, ToManyCont, ToOne)

from HWComponent import HWComponent

from Products.ZenModel.ZenossSecurity import (
    MANAGER_ROLE, MANAGE_NOTIFICATION_SUBSCRIPTIONS, MANAGE_TRIGGER,
    NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE, NOTIFICATION_UPDATE_ROLE,
    NOTIFICATION_VIEW_ROLE, OWNER_ROLE, TRIGGER_MANAGER_ROLE,
    TRIGGER_UPDATE_ROLE, TRIGGER_VIEW_ROLE, UPDATE_NOTIFICATION,
    UPDATE_TRIGGER, VIEW_NOTIFICATION, VIEW_TRIGGER, ZEN_ADD,
    ZEN_ADMINISTRATORS_EDIT, ZEN_ADMINISTRATORS_VIEW, ZEN_ADMIN_DEVICE,
    ZEN_CHANGE_ADMIN_OBJECTS, ZEN_CHANGE_ALERTING_RULES, ZEN_CHANGE_DEVICE,
    ZEN_CHANGE_DEVICE_PRODSTATE, ZEN_CHANGE_EVENT_VIEWS, ZEN_CHANGE_SETTINGS,
    ZEN_COMMON, ZEN_DEFINE_COMMANDS_EDIT, ZEN_DEFINE_COMMANDS_VIEW, ZEN_DELETE,
    ZEN_DELETE_DEVICE, ZEN_EDIT_LOCAL_TEMPLATES, ZEN_EDIT_USER,
    ZEN_EDIT_USERGROUP, ZEN_MAINTENANCE_WINDOW_EDIT,
    ZEN_MAINTENANCE_WINDOW_VIEW, ZEN_MANAGER_ROLE, ZEN_MANAGE_DEVICE,
    ZEN_MANAGE_DEVICE_STATUS, ZEN_MANAGE_DMD, ZEN_MANAGE_EVENTMANAGER,
    ZEN_MANAGE_EVENTS, ZEN_RUN_COMMANDS, ZEN_SEND_EVENTS, ZEN_UPDATE,
    ZEN_USER_ROLE, ZEN_VIEW, ZEN_VIEW_HISTORY, ZEN_VIEW_MODIFICATIONS,
    ZEN_ZPROPERTIES_EDIT, ZEN_ZPROPERTIES_VIEW)

class PowerSupply(HWComponent):
    """PowerSupply object"""

    portal_type = meta_type = 'PowerSupply'

    watts = None
    type = "unknown"
    state = "unknown"

    _properties = HWComponent._properties + (
        {'id':'watts', 'type':'int', 'mode':'w'},
        {'id':'type', 'type':'string', 'mode':'w'},
        {'id':'state', 'type':'string', 'mode':'w'},
    )

    _relations = HWComponent._relations + (
        ("hw", ToOne(ToManyCont, "Products.ZenModel.DeviceHW",
            "powersupplies")),
        )

    
    factory_type_information = ( 
        { 
            'id'             : 'PowerSupply',
            'meta_type'      : 'PowerSupply',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'PowerSupply_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addPowerSupply',
            'immediate_view' : 'viewPowerSupply',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'viewPowerSupply'
                , 'permissions'   : ('View',)
                },
                { 'id'            : 'perfConf'
                , 'name'          : 'Template'
                , 'action'        : 'objTemplates'
                , 'permissions'   : ("Change Device", )
                },
            )
          },
        )


    def wattsString(self):
        """
        Return a string representation of the watts
        """
        return self.watts is None and "unknown" or str(self.watts)


    def millivolts(self, default=None):
        """
        Return the current millivolts for the power supply
        """
        millivolts = self.cacheRRDValue('millivolts', default)
        if millivolts is not None:
            return long(millivolts)
        return None


    def millivoltsString(self):
        """
        Return the current millivolts as a string
        """
        millivolts = self.millivolts()
        return millivolts is None and "unknown" or "%dmv" % (millivolts,)


    def viewName(self):
        return self.id
    name = viewName


InitializeClass(PowerSupply)
