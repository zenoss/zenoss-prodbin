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

    _properties = (
        {'id':'sequence', 'type':'long', 'mode':'w'},
        )

    _relations =  (
        ('report', 
            ToOne(ToMany, 'Products.ZenModel.FancyReport', 'graphGroups')),
        ('collection', 
            ToOne(ToMany, 'Products.ZenModel.Collection', 'graphGroups')),
        ('graphDef',
            ToOne(ToMany, 'Products.ZenModel.GraphDefinition', 'graphGroups')),
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
    
    def getCollectionName(self):
        ''' Return the name of the collection
        '''
        if self.collection():
            return self.collection().id
        return ''


    def getGraphDefinitionName(self):
        ''' Return the name of the graphdef
        '''
        if self.graphDef():
            return self.graphDef().id
        return ''



        

InitializeClass(GraphGroup)
