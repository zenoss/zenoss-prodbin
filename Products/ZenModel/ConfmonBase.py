#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""ConfmonBase

base class for all confmon data objects.

$Id: ConfmonBase.py,v 1.50 2004/05/10 20:49:09 edahl Exp $"""

__version__ = "$Revision: 1.50 $"[11:-2]

import time

from Acquisition import aq_base
from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass
from DateTime import DateTime

from OFS.History import Historical

from Products.CMFCore.DynamicType import DynamicType
from Products.ZCatalog.CatalogAwareness import CatalogAware

from Products.ZenRelations.RelationshipManager import RelationshipManager
from Products.ZenRelations.Exceptions import SchemaError

from Products.ZenUtils.Utils import getSubObjects

from ConfmonPropManager import ConfmonPropManager
from ConfmonAll import ConfmonAll


class ConfmonBase(ConfmonAll, RelationshipManager, Historical, 
                    ConfmonPropManager, DynamicType, CatalogAware): 
    """
    Base class for all confmon classes
    """

    meta_type = 'ConfmonBase'

    default_catalog = ''

    manage_options = (
                        RelationshipManager.manage_options[:1] +
                        ConfmonPropManager.manage_options +
                        RelationshipManager.manage_options[1:]
                     )

    isInTree = 0 #should this class show in left nav tree

    security = ClassSecurityInfo()
   
    def __init__(self, id, title=None):
        self.createdTime = DateTime(time.time())
        RelationshipManager.__init__(self, id, title)

    
    security.declareProtected('View', 'primarySortKey')
    def primarySortKey(self):
        return self.getId()
    
        
    security.declareProtected('View', 'viewName')
    def viewName(self):
        return self.getId()
    
        
    def manage_afterAdd(self, item, container):
        """setup relationshipmanager add object to index and build relations """
        RelationshipManager.manage_afterAdd(self, item, container)
        self.buildRelations()
        if self.default_catalog: self.index_object()


    def manage_afterClone(self, item):
        RelationshipManager.manage_afterClone(self, item)
        if self.default_catalog: self.index_object()


    def manage_beforeDelete(self, item, container):
        RelationshipManager.manage_beforeDelete(self, item, container)
        if self.default_catalog: self.unindex_object()


    def index_object(self):
        """A common method to allow Findables to index themselves."""
        if hasattr(self, self.default_catalog):
            getattr(self, self.default_catalog).catalog_object(self, 
                                                self.getPrimaryUrlPath())

    def unindex_object(self):
        """A common method to allow Findables to unindex themselves."""
        if hasattr(self, self.default_catalog):
            key = self.getPrimaryUrlPath()
            cat = getattr(self, self.default_catalog)
            cat.uncatalog_object(key)

    #actions?
    def getTreeItems(self):
        nodes = []
        for item in self.objectValues():
            if hasattr(aq_base(item), "isInTree") and item.isInTree:
                nodes.append(item)
        return nodes
  

    def getClassPath(self):
        """path with quotes minus self id"""
        return '/'.join(self.getPrimaryPath()[:-1])


    def getSubObjects(self, filter=None, decend=None, retobjs=None):
        return getSubObjects(self, filter, decend, retobjs)


    def getCreatedTimeString(self):
        """return the creation time as a string"""
        return self.createdTime.strftime('%Y/%m/%d %H:%M:%S')


    def getModificationTimeString(self):
        """return the modification time as a string"""
        return self.bobobase_modification_time().strftime('%Y/%m/%d %H:%M:%S')


    def classificationDecend(self, obj):
        from Products.ZenModel.Classification import Classification
        return isinstance(obj, Classification)


    def classInstDecend(self, obj):
        from Products.ZenModel.Classification import Classification
        from Products.ZenModel.Instance import Instance
        return (isinstance(obj, Classification) or 
                isinstance(obj, Instance))


    def changePythonClass(self, newPythonClass, container):
        """change the python class of a persistent object"""
        id = self.id
        nobj = newPythonClass(id) #make new instance from new class
        nobj = nobj.__of__(container) #make aq_chain same as self
        nobj.oldid = self.id
        nobj.setPrimaryPath() #set up the primarypath for the copy
        #move all sub objects to new object
        nrelations = self.ZenSchemaManager.getRelations(nobj).keys()
        for sobj in self.objectValues():
            RelationshipManager._delObject(self,sobj.getId())
            if not hasattr(nobj, sobj.id) and sobj.id in nrelations:
                RelationshipManager._setObject(nobj, sobj.id, sobj)
        nobj.buildRelations() #build out any missing relations
        # copy properties to new object
        noprop = getattr(nobj, 'noPropertiesCopy', [])
        for name in nobj.getPropertyNames():
            if (getattr(self, name, None) and name not in noprop and
                hasattr(nobj, "_updateProperty")):
                val = getattr(self, name)
                nobj._updateProperty(name, val)
        return aq_base(nobj)
