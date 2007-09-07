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

__doc__="""CollectionItem

Defines attributes for how a data source will be graphed
and builds the nessesary rrd commands.
"""

import os

from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo, Permissions
from Products.ZenRelations.RelSchema import *
from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable

                                     
def manage_addCollectionItem(context, id, deviceId, compPath, sequence,
                                                            REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    CollectionItems.
    '''
    ci = CollectionItem(id)
    context._setObject(id, ci)
    ci.deviceId = deviceId
    ci.compPath = compPath
    ci.sequence = sequence
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() +'/manage_main') 

addCollectionItem = DTMLFile('dtml/addCollectionItem',globals())


class CollectionItem(ZenModelRM):
  
    meta_type = 'CollectionItem'

    sequence = 0
    deviceId = ''
    compPath = ''
    
    _properties = (
        {'id':'sequence', 'type':'long', 'mode':'w'},
        {'id':'deviceId', 'type':'string', 'mode':'w'},
        {'id':'compPath', 'type':'string', 'mode':'w'},
        )

    _relations = ZenPackable._relations + (
        ('collection', ToOne(ToMany,'Products.ZenModel.Collection','items')),
        )
    
    factory_type_information = ( 
        { 
            'immediate_view' : 'editCollectionItem',
            'actions'        :
            ( 
                { 'id'            : 'edit'
                , 'name'          : 'Collection Item'
                , 'action'        : 'editCollectionItem'
                , 'permissions'   : ( Permissions.view, )
                },
            )
        },
    )


    def __init__(self, id, deviceId, compPath, sequence, 
                                            title=None, buildRelations=True):
        ZenModelRM.__init__(self, id, title, buildRelations)
        self.deviceId = deviceId
        self.compPath = compPath
        self.sequence = sequence


    def getDevice(self):
        return self.dmd.Devices.findDevice(self.deviceId)


    def getComponent(self):
        component = self.getDevice()
        for part in self.compPath.split('/'):
            if part:
                component = getattr(component, part)
        return component

InitializeClass(CollectionItem)
