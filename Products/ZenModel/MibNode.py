##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Globals
from AccessControl import Permissions
from Products.ZenModel.ZenossSecurity import *

from Products.ZenRelations.RelSchema import *

from MibBase import MibBase

class MibNode(MibBase):

    #syntax = ""
    access = ""

    _properties = MibBase._properties + (
        {'id':'access', 'type':'string', 'mode':'w'},
    )

    _relations = MibBase._relations + (
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
            )
         },
        )
