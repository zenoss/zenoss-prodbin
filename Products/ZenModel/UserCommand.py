#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
#from Acquisition import aq_parent
from ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *
#from DateTime import DateTime
#from Products.PageTemplates.Expressions import getEngine
#from Products.ZenUtils.ZenTales import talesCompile
#from Products.ZenUtils.Utils import setWebLoggingStream, clearWebLoggingStream
#import logging
#log = logging.getLogger("zen.Device")


manage_addUserCommand = DTMLFile('dtml/addUserCommand',globals())

class UserCommand(ZenModelRM):

    meta_type = 'UserCommand'

    security = ClassSecurityInfo()
  
    description = ""
    command = ''

    _properties = (
        {'id':'description', 'type':'text', 'mode':'w'},
        {'id':'command', 'type':'text', 'mode':'w'},
        )

    _relations =  (
        ("commandable", ToOne(ToManyCont, 'Commandable', 'userCommands')),
        )


    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
    { 
        'immediate_view' : 'userCommandDetail',
        'actions'        :
        ( 
            {'id'            : 'overview',
             'name'          : 'User Command',
             'action'        : 'userCommandDetail',
             'permissions'   : ( Permissions.view, ),
            },
            { 'id'            : 'viewHistory',
              'name'          : 'Changes',
              'action'        : 'viewHistory',
              'permissions'   : ( Permissions.view, ),
            }
        )
    },
    )

    security.declareProtected('View', 'breadCrumbs')
    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object
        [('url','id'), ...]
        """
        crumbs = super(UserCommand, self).breadCrumbs(terminator)
        commType = self.commandable().meta_type
        if commType == 'Device':
            crumb = (crumbs[-2][0] + '/deviceManagement', 'manage')
        elif commType in ['DeviceClass', 'System', 'DeviceGroup', 'Location']:
            crumb = (crumbs[-2][0] + '/deviceOrganizerManage', 'manage')
        elif commType == 'ServiceOrganizer':
            crumb = (crumbs[-2][0] + '/serviceOrganizerManage', 'manage')
        elif commType == 'ServiceClass':
            crumb = (crumbs[-2][0] + '/serviceClassManage', 'manage')
        #elif commType == 'Service':
        #    crumb = (crumbs[-2][0] + '/serviceManage', 'manage')
        elif commType == 'OSProcessOrganizer':
            crumb = (crumbs[-2][0] + '/osProcessOrganizerManage', 'manage')
        elif commType == 'OSProcessClass':
            crumb = (crumbs[-2][0] + '/osProcessClassManage', 'manage')
        #elif commType == 'OSProcess':
        #    crumb = (crumbs[-2][0] + '/serviceManage', 'manage')
        else:
            raise 'huh? %s' % self.commandable().meta_type
            crumb = None
        if crumb:
            crumbs.insert(-1, crumb)
        return crumbs



    #def isEditable(self, context):
    #    """Is this template editable in context.
    #    """
    #    return (self.isManager() and 
    #            (context == self or context.isLocalName(self.id)))

    
    #def getUserCommmandPath(self):
    #    """Return the path on which this command is defined.
    #    """
    #    return self.getPrimaryParent().getPrimaryDmdId(subrel="UserCommands")
        

InitializeClass(UserCommand)
