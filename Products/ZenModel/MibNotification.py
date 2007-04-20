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

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions

from Products.ZenRelations.RelSchema import *

from MibBase import MibBase

class MibNotification(MibBase):

    objects = []
    
    
    _properties = MibBase._properties + (
        {'id':'objects', 'type':'lines', 'mode':'w'},
    )
    
    _relations = (
        ("module", ToOne(ToManyCont, "Products.ZenModel.MibModule", "notifications")),
    )
    
    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'immediate_view' : 'viewMibNotification',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewMibNotification'
                , 'permissions'   : ( Permissions.view, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : ( Permissions.view, )
                },
            )
         },
        )
