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

import re

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from Acquisition import aq_base
from Commandable import Commandable
from Products.ZenRelations.RelSchema import *

from ZenModelRM import ZenModelRM


def manage_addOSProcessClass(context, id=None, REQUEST = None):
    """make a device class"""
    if id:
        context.manage_addOSProcessClass(id)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addOSProcessClass = DTMLFile('dtml/addOSProcessClass',globals())

class OSProcessClass(ZenModelRM, Commandable):
    meta_type = "OSProcessClass"
    dmdRootName = "Processes"
    default_catalog = "processSearch"

    name = ""
    regex = ""
    ignoreParameters = False
    description = ""
    sequence = 0
    
    _properties = (
        {'id':'name', 'type':'string', 'mode':'w'},
        {'id':'regex', 'type':'string', 'mode':'w'},
        {'id':'ignoreParameters', 'type':'boolean', 'mode':'w'},
        {'id':'description', 'type':'text', 'mode':'w'},
        {'id':'sequence', 'type':'int', 'mode':'w'},
        ) 

    _relations = (
        ("instances", ToMany(ToOne, "Products.ZenModel.OSProcess", "osProcessClass")),
        ("osProcessOrganizer", 
            ToOne(ToManyCont,"Products.ZenModel.OSProcessOrganizer","osProcessClasses")),
        ('userCommands', ToManyCont(ToOne, 'Products.ZenModel.UserCommand', 'commandable')),
        )


    factory_type_information = ( 
        { 
            'immediate_view' : 'osProcessClassStatus',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'osProcessClassStatus'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'osProcessClassEdit'
                , 'permissions'   : ("Manage DMD", )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'osProcessClassManage'
                , 'permissions'   : ("Manage DMD",)
                },
                { 'id'            : 'zproperties'
                , 'name'          : 'zProperties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Change Device",)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Modifications'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  Permissions.view, )
                },
            )
         },
        )
    
    security = ClassSecurityInfo()
   

    def __init__(self, id):
        id = self.prepId(id)
        super(OSProcessClass, self).__init__(id)
        self.name = self.regex = id

  
    def getOSProcessClassName(self):
        """Return the full name of this process class.
        """
        return self.getPrimaryDmdId("Processes", "osProcessClasses")


    def match(self, procKey):
        """match procKey against our regex.
        """
        return re.search(self.regex, procKey)

        
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
                                  regex="",
                                  description="",
                                  ignoreParameters=False,
                                  REQUEST=None):
                                 
        """
        Edit a ProductClass from a web page.
        """
        # Left in name, added title for consistency
        self.title = name
        self.name = name
        id = self.prepId(name)
        redirect = self.rename(id)
        self.regex = regex        
        self.description = description
        self.ignoreParameters = ignoreParameters
        self.zMonitor = zMonitor
        if REQUEST:
            from Products.ZenUtils.Time import SaveMessage
            REQUEST['message'] = SaveMessage()
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
        
        
        


InitializeClass(OSProcessClass)
