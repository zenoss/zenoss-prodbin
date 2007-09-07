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

__doc__="""Collection

Collection is a grouping of devices and components.
"""


from AccessControl import Permissions
from Globals import InitializeClass
from Globals import DTMLFile
from Products.ZenRelations.RelSchema import *
from ZenModelRM import ZenModelRM


def manage_addCollection(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    Collections.
    '''
    c = Collection(id)
    context._setObject(id, c)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() +'/manage_main') 

addCollection = DTMLFile('dtml/addCollection',globals())


class Collection(ZenModelRM):
    '''
    '''
    
    meta_type = 'Collection'
   
    _properties = (
        )

    _relations =  (
        ('graphGroups', 
            ToMany(ToMany,'Products.ZenModel.GraphGroup', 'collection')),
        ('items',
            ToMany(ToOne, 'Products.ZenModel.CollectionItem', 'collection')),
        )

    factory_type_information = ( 
    { 
        'immediate_view' : 'editCollection',
        'actions'        :
        ( 
            { 'id'            : 'edit'
            , 'name'          : 'Collection'
            , 'action'        : 'editCollection'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )
    
    def manage_addCollectionItem(self, new_id, deviceId, compPath, 
                                                    REQUEST=None):
        ''' Create a new CollectionItem and add to this collection
        '''
        from CollectionItem import CollectionItem
        item = CollectionItem(new_id, deviceId, compPath, len(self.items))
        self.items._setObject(item.id, item)
        if REQUEST:
            REQUEST['message'] = 'Item added'
            self.callZenScreen(REQUEST)
        return item

    def getNumItems(self):
        ''' Return the number of collection items
        '''
        return len(self.items())
        
InitializeClass(Collection)
