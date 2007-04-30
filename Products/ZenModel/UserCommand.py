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

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
from ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *


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
        ("commandable", ToOne(ToManyCont, 'Products.ZenModel.Commandable', 'userCommands')),
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
              'name'          : 'Modifications',
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
        manageTab = self.commandable().getPathToManageTab()
        if manageTab:
            crumb = (manageTab, 'manage')
            crumbs.insert(-1, crumb)
        return crumbs
        

InitializeClass(UserCommand)
