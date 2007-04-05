#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""ExpansionCard

ExpansionCard is a collection of devices and subsystems that make
up a business function

$Id: ExpansionCard.py,v 1.7 2004/04/06 22:33:24 edahl Exp $"""

__version__ = "$Revision: 1.7 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass

from Products.ZenRelations.RelSchema import *

from HWComponent import HWComponent

class ExpansionCard(HWComponent):
    """ExpansionCard object"""

    portal_type = meta_type = 'ExpansionCard'

    slot = ""

    # we don't monitor cards
    monitor = False

    _properties = HWComponent._properties + (
        {'id':'slot', 'type':'int', 'mode':'w'},
    )

    _relations = HWComponent._relations + (
        ("hw", ToOne(ToManyCont, "Products.ZenModel.DeviceHW", "cards")),
        )

    
    factory_type_information = ( 
        { 
            'id'             : 'ExpansionCard',
            'meta_type'      : 'ExpansionCard',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'ExpansionCard_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addExpansionCard',
            'immediate_view' : 'viewExpansionCard',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'viewExpansionCard'
                , 'permissions'   : ('View',)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : ('View',)
                },
            )
          },
        )

InitializeClass(ExpansionCard)
