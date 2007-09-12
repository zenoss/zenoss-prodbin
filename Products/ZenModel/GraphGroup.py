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

__doc__="""GraphGroup

GraphGroup contains the settings, graphDefinitions and collections
that form part of an UberReport.
"""


from AccessControl import Permissions
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from Products.ZenRelations.RelSchema import *
from ZenModelRM import ZenModelRM


def manage_addGraphGroup(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    '''
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() +'/manage_main') 


class GraphGroup(ZenModelRM):
    '''
    '''
    
    meta_type = 'GraphGroup'
   
    sequence = 0
    collectionId = ''
    graphDefId = ''

    _properties = (
        {'id':'sequence', 'type':'long', 'mode':'w'},
        {'id':'collectionId', 'type':'string', 'mode':'w'},
        {'id':'graphDefId', 'type':'string', 'mode':'w'},        
        )

    _relations =  (
        ('report', 
            ToOne(ToMany, 'Products.ZenModel.FancyReport', 'graphGroups')),
        )

    factory_type_information = ( 
    { 
        'immediate_view' : 'editGraphGroup',
        'actions'        :
        ( 
            { 'id'            : 'edit'
            , 'name'          : 'Graph Group'
            , 'action'        : 'editGraphGroup'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )

    security = ClassSecurityInfo()

    def __init__(self, newId, collectionId='', graphDefId='', sequence=0,
                                            title=None, buildRelations=True):
        ZenModelRM.__init__(self, newId, title, buildRelations)
        self.collectionId = collectionId
        self.graphDefId = graphDefId
        self.sequence = sequence

        
    # security.declareProtected('Manage DMD', 'manage_chooseCollection')
    # def manage_chooseCollection(self, collectionId, REQUEST):
    #     ''' Set the collection or create a new one with the given id
    #     '''
    #     if collectionId in self.collections.objectIds():
    #         self.collectionId = collectionId
    #         REQUEST['RESPONSE'].redirect('%s/chooseGraphDef'
    #             % self.getPrimaryUrlPath())
    #     else:
    #         from Collection import Collection
    #         newId = self.getUniqueId('collections', collectionId)
    #         col = Collection(newId)
    #         self.collections._setObject(col.id, col)
    #         REQUEST['RESPONSE'].redirect('%s/createCollection'
    #             % self.getPrimaryUrlPath())

    def getNewGraphDefUrl(self):
        ''' Get the url for creating a new graph definition
        '''
        return ''


    def getCollection(self):
        ''' Return the referenced collection or None if it doesn't exist
        '''
        return getattr(self.collections, self.collectionId, None)


    def getGraphDef(self):
        ''' Return the referenced graphDef or None if it doesn't exist
        '''
        return getattr(self.graphDefs, self.graphDefId, None)


InitializeClass(GraphGroup)
