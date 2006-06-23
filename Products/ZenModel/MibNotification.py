#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

from Products.ZenRelations.RelSchema import *

from MibBase import MibBase

class MibNotification(MibBase):

    objects = []
    
    
    _properties = MibBase._properties + (
        {'id':'objects', 'type':'lines', 'mode':'w'},
    )
    
    _relations = (
        ("module", ToOne(ToManyCont, "MibModule", "notifications")),
    )
