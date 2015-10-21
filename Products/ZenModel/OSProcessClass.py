##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007-2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import re

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
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
from Products.ZenModel.OSProcessMatcher import OSProcessClassMatcher
from Commandable import Commandable
from Products.ZenRelations.RelSchema import (
    RELMETATYPES, RelSchema, ToMany, ToManyCont, ToOne)
from Products.ZenWidgets import messaging
from ZenPackable import ZenPackable
from zope.component import adapter
from OFS.interfaces import IObjectWillBeRemovedEvent
from ZenModelRM import ZenModelRM

def manage_addOSProcessClass(context, id=None, REQUEST = None):
    """make a device class"""
    if id:
        context.manage_addOSProcessClass(id)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addOSProcessClass = DTMLFile('dtml/addOSProcessClass',globals())

class OSProcessClass(ZenModelRM, Commandable, ZenPackable, OSProcessClassMatcher):
    meta_type = "OSProcessClass"
    dmdRootName = "Processes"
    default_catalog = "processSearch"

    name = ""
    regex = ""
    excludeRegex = "\\b(vim|tail|grep|tar|cat|bash)\\b"
    replaceRegex = ""
    replacement = ""
    ignoreParametersWhenModeling = False
    ignoreParameters = False
    description = ""
    example = ""
    sequence = 0
    
    _properties = (
        {'id':'name', 'type':'string', 'mode':'w'},
        {'id':'regex', 'type':'string', 'mode':'w'},
        {'id':'excludeRegex', 'type':'string', 'mode':'w'},
        {'id':'replaceRegex', 'type':'string', 'mode':'w'},
        {'id':'replacement', 'type':'string', 'mode':'w'},
        {'id':'ignoreParametersWhenModeling', 'type':'boolean', 'mode':'w'},
        {'id':'ignoreParameters', 'type':'boolean','mode':'w'},
        {'id':'description', 'type':'text', 'mode':'w'},
        {'id':'sequence', 'type':'int', 'mode':'w'},
        {'id':'example', 'type':'string', 'mode':'w'},
        )

    _relations = ZenPackable._relations + (
        ("instances", ToMany(ToOne, "Products.ZenModel.OSProcess", "osProcessClass")),
        ("osProcessOrganizer", 
            ToOne(ToManyCont,"Products.ZenModel.OSProcessOrganizer","osProcessClasses")),
        ('userCommands', ToManyCont(ToOne, 'Products.ZenModel.UserCommand', 'commandable')),
        )
    
    security = ClassSecurityInfo()
   

    def __init__(self, id):
        id = self.prepId(id)
        super(OSProcessClass, self).__init__(id)
        self.name = self.includeRegex = id

    def getOSProcessClassName(self):
        """Return the full name of this process class.
        """
        return self.getPrimaryDmdId("Processes", "osProcessClasses")
        
    def count(self):
        """Return count of instances in this class.
        """
        return self.instances.countObjects()


    security.declareProtected('Manage DMD', 'manage_editOSProcessClass')
    def manage_editOSProcessClass(self,
                                  name="",
                                  zMonitor=True, 
                                  zAlertOnRestart=False,
                                  zFailSeverity=3,
                                  includeRegex="",
                                  excludeRegex="",
                                  replaceRegex="",
                                  replacement="",
                                  description="",
                                  REQUEST=None):
                                 
        """
        Edit a ProcessClass from a web page.
        """
        from Products.ZenUtils.Utils import unused
        unused(zAlertOnRestart, zFailSeverity, zMonitor)
        # Left in name, added title for consistency
        self.name = name
        id = self.prepId(name)
        redirect = self.rename(id)
        self.includeRegex = includeRegex
        self.excludeRegex = excludeRegex
        self.replaceRegex = replaceRegex
        self.replacement = replacement
        self.description = description
        if REQUEST:
            from Products.ZenUtils.Time import SaveMessage
            messaging.IMessageSender(self).sendToBrowser(
                'Process Class Saved',
                SaveMessage()
            )
            return self.callZenScreen(REQUEST, redirect)
   

    def getUserCommandTargets(self):
        ''' Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        '''
        return self.instances()
        
    
    def getUrlForUserCommands(self):
        return self.getPrimaryUrlPath() + '/osProcessClassManage'


    def getPrimaryParentOrgName(self):
        ''' Return the organizer name for the primary parent
        '''
        return self.getPrimaryParent().getOrganizerName()

    @property
    def includeRegex(self):
        return self.regex

    @includeRegex.setter
    def includeRegex(self, value):
        self.regex = value

    @property
    def title(self):
        return self.name or self.id

    @title.setter
    def title(self, value):
        self.name = value

    def processClassPrimaryUrlPath(self):
        return self.getPrimaryUrlPath()

InitializeClass(OSProcessClass)

@adapter(OSProcessClass, IObjectWillBeRemovedEvent)
def onProcessClassRemoved(ob, event):
    # if _operation is set to 1 it means we are moving it, not deleting it
    if getattr(ob, '_operation', None) != 1:
        for i in ob.instances():
            i.manage_deleteComponent()
        
