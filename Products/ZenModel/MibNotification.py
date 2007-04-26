#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

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
                , 'name'          : 'Modifications'
                , 'action'        : 'viewHistory'
                , 'permissions'   : ( Permissions.view, )
                },
            )
         },
        )
