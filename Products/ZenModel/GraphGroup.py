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
    combineDevices = False

    _properties = (
        {'id':'sequence', 'type':'long', 'mode':'w'},
        {'id':'collectionId', 'type':'string', 'mode':'w'},
        {'id':'graphDefId', 'type':'string', 'mode':'w'},        
        {'id':'combineDevices', 'type':'boolean', 'mode':'w'},        
        )

    _relations =  (
        ('report', 
            ToOne(ToMany, 'Products.ZenModel.MultiGraphReport', 'graphGroups')),
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


    def getCollection(self):
        ''' Return the referenced collection or None if it doesn't exist
        '''
        return getattr(self.report.collections, self.collectionId, None)


    def getGraphDef(self):
        ''' Return the referenced graphDef or None if it doesn't exist
        '''
        return self.report().getGraphDef(self.graphDefId)


    def getCollectionUrl(self):
        '''
        '''
        collection = self.getCollection()
        url = None
        if collection:
            url = collection.getPrimaryUrlPath()
        return url


    def getGraphDefUrl(self):
        '''
        '''
        graphDef = self.getGraphDef()
        url = None
        if graphDef:
            url = graphDef.getPrimaryUrlPath()
        return url


    def zmanage_editProperties(self, REQUEST):
        ''' Save then redirect back to the report
        '''
        self.manage_changeProperties(**REQUEST.form)
        index_object = getattr(self, 'index_object', lambda self: None)
        index_object()
        REQUEST['RESPONSE'].redirect(self.report().getPrimaryUrlPath())


InitializeClass(GraphGroup)
