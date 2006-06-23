#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

from Products.ZenRelations.RelSchema import *

from MibBase import MibBase

class MibNode(MibBase):

    #syntax = ""
    access = ""

    _properties = MibBase._properties + (
        {'id':'access', 'type':'string', 'mode':'w'},
    )

    _relations = (
        ("module", ToOne(ToManyCont, "MibModule", "nodes")),
    )
