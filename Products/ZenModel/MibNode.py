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

class MibNode(MibBase):

    #syntax = ""
    access = ""

    _properties = MibBase._properties + (
        {'id':'access', 'type':'string', 'mode':'w'},
    )

    _relations = (
        ("module", ToOne(ToManyCont, "Products.ZenModel.MibModule", "nodes")),
    )
    
    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'immediate_view' : 'viewMibNode',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewMibNode'
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


