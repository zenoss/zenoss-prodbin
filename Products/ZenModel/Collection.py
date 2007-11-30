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


from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
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
        return REQUEST['RESPONSE'].redirect(context.absolute_url() +'/manage_main') 

addCollection = DTMLFile('dtml/addCollection',globals())


class Collection(ZenModelRM):
    ''' Holds an assortment of devices and/or components.
    '''
    
    meta_type = 'Collection'
   
    _properties = (
        )

    _relations =  (
        ('report',
            ToOne(ToManyCont, 'Products.ZenModel.MultiGraphReport', 'collections')),
        ('items',
            ToManyCont(ToOne, 'Products.ZenModel.CollectionItem', 'collection')),
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
    
    security = ClassSecurityInfo()

    
    def createCollectionItem(self, orgPath='', devId='', compPath='',
                            recurse=False, checkExists=False):
        ''' Create and insert a new CollectionItem based either on the
        orgPath or on devId/compPath.  Returns the new item.
        '''
        from CollectionItem import CollectionItem
        ci = CollectionItem(self.getUnusedId('items', 'Item'))
        if orgPath:
            ci.deviceOrganizer = orgPath
        else:
            ci.deviceId = devId
            ci.compPath = compPath
        ci.recurse = recurse
        ci.sequence = len(self.items())
        self.items._setObject(ci.id, ci)
        ci = self.items._getOb(ci.id)
        # This check happens after the _setObject so that ci has full 
        # aq wrapper in case it needs it.
        if checkExists and not ci.getRepresentedItem():
            self.items._delObject(ci.id)
            ci = None
        return ci


    security.declareProtected('Manage DMD', 'manage_addCollectionItem')
    def manage_addCollectionItem(self, itemType,
            deviceIds=(), componentPaths=(), deviceClasses=(), systems=(),
            groups=(), locations=(), recurse=False, REQUEST=None):
        ''' Create a new CollectionItem and add to this collection
        '''
        count = 0
        if itemType == 'devcomp':
            if not deviceIds:
                deviceIds = []
            if not componentPaths:
                componentPaths = ['']
            for i, devId in enumerate(deviceIds):
                for cPath in componentPaths:
                    ci = self.createCollectionItem(devId=devId, compPath=cPath,
                        recurse=False, checkExists=True)
                    if ci:
                        count += 1
        if itemType == 'deviceClass':
            for dClass in deviceClasses:
                self.createCollectionItem(
                                    orgPath='/Devices' + dClass, recurse=recurse)
            count += 1
        if itemType == 'system':
            for system in systems:
                self.createCollectionItem(
                                    orgPath='/Systems' + system, recurse=recurse)
                count += 1
        if itemType == 'group':
            for group in groups:
                self.createCollectionItem(
                                    orgPath='/Groups' + group, recurse=recurse)
                count += 1
        if itemType == 'location':
            for loc in locations:
                self.createCollectionItem(
                                    orgPath='/Locations' + loc, recurse=recurse)
                count += 1
            
        if REQUEST:
            REQUEST['message'] = ' %s item%s added' % (count,
                count > 1 and 's' or '')
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'manage_deleteCollectionItems')
    def manage_deleteCollectionItems(self, ids=(), REQUEST=None):
        ''' Delete collection items from this report
        '''
        for id in ids:
            self.items._delObject(id)
        self.manage_resequenceCollectionItems()
        if REQUEST:
            REQUEST['message'] = 'Item%s deleted' % (len(ids) > 1 and 's' or '')
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'manage_resequenceCollectionItems')
    def manage_resequenceCollectionItems(self, seqmap=(), origseq=(), 
                                                                REQUEST=None):
        """Reorder the sequence of the items.
        """
        from Products.ZenUtils.Utils import resequence
        return resequence(self, self.items(), seqmap, origseq, REQUEST)


    security.declareProtected('Manage DMD', 'getItems')
    def getItems(self):
        ''' Return an ordered list of CollectionItems
        '''
        import sys
        def cmpItems(a, b):
            try: a = int(a.sequence)
            except ValueError: a = sys.maxint
            try: b = int(b.sequence)
            except ValueError: b = sys.maxint
            return cmp(a, b)
        items =  self.items()[:]
        items.sort(cmpItems)
        return items
        

    def getNumItems(self):
        ''' Return the number of collection items
        '''
        return len(self.items())


    def getDevicesAndComponents(self):
        ''' Return a deduped list of devices and components represented
        by this collection's collectionitems
        '''
        things = {}
        for collectionItem in self.items():
            devsAndComps = collectionItem.getDevicesAndComponents()
            for devOrComp in devsAndComps:
                things[devOrComp.getPrimaryId()] = devOrComp
        return things.values()

        
InitializeClass(Collection)
