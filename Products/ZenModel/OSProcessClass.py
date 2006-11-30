#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

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
        sc = OSProcessClass(id)
        context._setObject(id, sc)
        sc = context._getOb(id)
        sc.createCatalog()
        sc.buildZProperties()

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
    
    _properties = (
        {'id':'name', 'type':'string', 'mode':'w'},
        {'id':'regex', 'type':'string', 'mode':'w'},
        {'id':'ignoreParameters', 'type':'boolean', 'mode':'w'},
        {'id':'description', 'type':'text', 'mode':'w'},
        ) 

    _relations = (
        ("instances", ToMany(ToOne, "OSProcess", "osProcessClass")),
        ("osProcessOrganizer", 
            ToOne(ToManyCont,"OSProcessOrganizer","osProcessClasses")),
        ('userCommands', ToManyCont(ToOne, 'UserCommand', 'commandable')),
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
                , 'name'          : 'Manage'
                , 'action'        : 'osProcessClassManage'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'zproperties'
                , 'name'          : 'zProperties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Change Device",)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
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
        self.name = name
        id = self.prepId(name)
        redirect = self.rename(id)
        self.regex = regex        
        self.description = description
        self.ignoreParameters = ignoreParameters
        if REQUEST:
            REQUEST['message'] = "Saved at time:"
            return self.callZenScreen(REQUEST, redirect)
   

    def getUserCommandTargets(self):
        ''' Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        '''
        return self.instances()        


InitializeClass(OSProcessClass)
