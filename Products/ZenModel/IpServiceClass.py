##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Globals import DTMLFile
from Globals import InitializeClass

from AccessControl import Permissions
from AccessControl import ClassSecurityInfo
from Products.ZenModel.ZenossSecurity import MANAGER_ROLE, MANAGE_NOTIFICATION_SUBSCRIPTIONS, MANAGE_TRIGGER, NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE, NOTIFICATION_UPDATE_ROLE, NOTIFICATION_VIEW_ROLE, OWNER_ROLE, TRIGGER_MANAGER_ROLE, TRIGGER_UPDATE_ROLE, TRIGGER_VIEW_ROLE, UPDATE_NOTIFICATION, UPDATE_TRIGGER, VIEW_NOTIFICATION, VIEW_TRIGGER, ZEN_ADD, ZEN_ADMINISTRATORS_EDIT, ZEN_ADMINISTRATORS_VIEW, ZEN_ADMIN_DEVICE, ZEN_CHANGE_ADMIN_OBJECTS, ZEN_CHANGE_ALERTING_RULES, ZEN_CHANGE_DEVICE, ZEN_CHANGE_DEVICE_PRODSTATE, ZEN_CHANGE_EVENT_VIEWS, ZEN_CHANGE_SETTINGS, ZEN_COMMON, ZEN_DEFINE_COMMANDS_EDIT, ZEN_DEFINE_COMMANDS_VIEW, ZEN_DELETE, ZEN_DELETE_DEVICE, ZEN_EDIT_LOCAL_TEMPLATES, ZEN_EDIT_USER, ZEN_EDIT_USERGROUP, ZEN_MAINTENANCE_WINDOW_EDIT, ZEN_MAINTENANCE_WINDOW_VIEW, ZEN_MANAGER_ROLE, ZEN_MANAGE_DEVICE, ZEN_MANAGE_DEVICE_STATUS, ZEN_MANAGE_DMD, ZEN_MANAGE_EVENTMANAGER, ZEN_MANAGE_EVENTS, ZEN_RUN_COMMANDS, ZEN_SEND_EVENTS, ZEN_UPDATE, ZEN_USER_ROLE, ZEN_VIEW, ZEN_VIEW_HISTORY, ZEN_VIEW_MODIFICATIONS, ZEN_ZPROPERTIES_EDIT, ZEN_ZPROPERTIES_VIEW

from Products.ZenRelations.RelSchema import RELMETATYPES, RelSchema, ToMany, ToManyCont, ToOne

from ServiceClass import ServiceClass


def manage_addIpServiceClass(context, id, REQUEST = None):
    """make a device"""
    ipsc = IpServiceClass(id)
    context._setObject(ipsc.id, ipsc)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main') 
    return ipsc.id


addIpServiceClass = DTMLFile('dtml/addIpServiceClass',globals())

class IpServiceClass(ServiceClass):
    """IpServiceClass object.
    """
    __pychecker__='no-override'

    sendString = ""
    expectRegex = ""

    portal_type = meta_type = 'IpServiceClass'

    _properties = ServiceClass._properties + (
        {'id':'sendString', 'type':'string', 'mode':'w'},
        {'id':'expectRegex', 'type':'string', 'mode':'w'},
        )

    factory_type_information = (
        { 
            'immediate_view' : 'ipServiceClassStatus',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'ipServiceClassStatus'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'ipServiceClassEdit'
                , 'permissions'   : ("Manage DMD", )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'ipServiceClassManage'
                , 'permissions'   : ("Manage DMD",)
                },
                { 'id'            : 'zproperties'
                , 'name'          : 'zProperties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Change Device",)
                },
            )
         },
        )
    
    security = ClassSecurityInfo()
    
    def __init__(self, id, serviceKeys=(), description="", port=0):
        ServiceClass.__init__(self, id, serviceKeys, description)
        self._updateProperty('port', port)


    security.declareProtected('Manage DMD', 'manage_editServiceClass')
    def manage_editServiceClass(self, name="", monitor=False, serviceKeys="",
                               port=0, description="", sendString="",
                               expectRegex="", REQUEST=None):
        """
        Edit a ProductClass from a web page.
        """
        self.sendString = sendString
        self.expectRegex = expectRegex
        return super(IpServiceClass,self).manage_editServiceClass(
                                name, monitor, serviceKeys,
                                port, description, REQUEST=REQUEST)
   


InitializeClass(IpServiceClass)
