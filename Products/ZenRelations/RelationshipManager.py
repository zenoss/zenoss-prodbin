#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""RelationshipManager

RelationshipManager is a mix in class to manage relationships
defined by the SchemaManager.  

$Id: RelationshipManager.py,v 1.41 2004/04/13 22:02:18 edahl Exp $"""

__version__ = "$Revision: 1.41 $"[11:-2]

import types
import logging

# Base classes for RelationshipManager
from PrimaryPathObjectManager import PrimaryPathObjectManager
from ZenPropertyManager import ZenPropertyManager

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from Acquisition import aq_base
from App.Management import Tabs

from RelSchema import *
from Exceptions import *
from utils import importClass

zenmarker = "__ZENMARKER__"


def manage_addRelationshipManager(context, id, title=None, REQUEST = None):
    """Relationship factory"""
    rm =  RelationshipManager(id)
    context._setObject(id, rm)
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

addRelationshipManager = DTMLFile('dtml/addRelationshipManager',globals())


class RelationshipManager(PrimaryPathObjectManager, ZenPropertyManager):
    """
    RelationshipManger is an ObjectManager like class that can contain
    relationships (in fact relationships can only be added to a 
    RelationshipManager).

    Relationships are defined on an RM by the hash _relations.  It
    should be defined on the class so that it isn't stored in the database.
    If there is inheritance involved remember to add the base class _relations
    definition to the current class so that all relationships for the class
    are defined on it.

    remoteClassStr - is a string that represents the full path to the remote
                    class.  Its a string because in most cases the classes
                    will be in different modules which would cause a recursive
                    import of the two modules.
                    
    zenRelationsBaseModule - can be defined on a class or in its aq_chain to
                    Append a classes module to remoteClassStr.  If the class
                    is defined in a file named the same as the class the lookup
                    will automatically append the final class name to the path.
                    ie Products.ZenModel.Device will lookup the class
                    Products.ZenModel.Device.Device defined in the file 
                    Device.py.

    _relations = (
        ("toonename", ToOne(ToMany, remoteClassStr, remoteName)), 
        ("tomanyname", ToMany(ToMany, remoteClassStr, remoteName)), 
        )
    """ 

    _relations = ()

    meta_type = 'Relationship Manager'
   
    security = ClassSecurityInfo()

    manage_options = (
        PrimaryPathObjectManager.manage_options + 
        ZenPropertyManager.manage_options
        )

    manage_main=DTMLFile('dtml/RelationshipManagerMain', globals())


    def __init__(self, id, title=None, buildRelations=True):
        self.id = id
        self._operation = -1
        if buildRelations: self.buildRelations()

    
    ##########################################################################
    #
    # Methods for relationship management.
    #
    ##########################################################################

    
    def addRelation(self, name, obj):
        """Form a bi-directional relationship."""
        rel = getattr(self, name, None)
        if rel == None: 
            raise AttributeError("Relationship %s, not found" % name)
        rel.addRelation(obj)


    def removeRelation(self, name, obj = None):
        """
        Remove an object from a relationship. 
        If no object is passed all objects are removed.
        """
        rel = getattr(self, name, None)
        if rel == None: 
            raise AttributeError("Relationship %s, not found" % name)
        rel.removeRelation(obj)


    def _setObject(self,id,object,roles=None,user=None,set_owner=1):
        if object.meta_type in RELMETATYPES:
            schema = self.lookupSchema(id)
            if not schema.checkType(object):
                raise ZenSchemaError("Relaitonship %s type %s != %s" %
                            (id, object.meta_type, schema.__class__.__name__))
        return PrimaryPathObjectManager._setObject(self, id, object, roles, 
                                            user, set_owner)                


    def manage_beforeDelete(self, item, container):
        """
        handle cut/past vs. delete
        If we are being moved (cut/past) don't clear relationshp
        if we are being deleted set all relationship to None so
        that our related object don't have dangling references
        """
        PrimaryPathObjectManager.manage_beforeDelete(self, item, container)
        if self._operation > -1: self._operation = -1


    ##########################################################################
    #
    # Methods for copy management
    #
    ##########################################################################

    def _getCopy(self, container):
        """
        Create a copy of this relationship manager.  This involes copying
        relationships and removing invalid relations (ie ones with ToOne)
        and performing copies of any contained objects.
        Properties are also set on the new object.
        """
        id = self.id
        if getattr(aq_base(container), id, zenmarker) is not zenmarker:
            id = "copy_of_" + id
        cobj = self.__class__(id, buildRelations=False) #make new instance
        cobj = cobj.__of__(container) #give the copy container's aq chain
        for sobj in self.objectValues():
            csobj = sobj._getCopy(cobj)
            cobj._setObject(csobj.id, csobj)
        noprop = getattr(self, 'zNoPropertiesCopy', [])
        for name, value in self.propertyItems():
            cobj._updateProperty(name, value)
        return aq_base(cobj)
                
    
    def _notifyOfCopyTo(self, container, op=0):
        """Manage copy/move/rename state for use in manage_beforeDelete."""
        self._operation = op # 0 == copy, 1 == move, 2 == rename


    def cb_isMoveable(self):
        """Prevent move unless we are being called from our primary path."""
        if (self.getPhysicalPath() == self.getPrimaryPath()):
            return PrimaryPathObjectManager.cb_isMoveable(self)
        return 0


    ##########################################################################
    #
    # Functions for examining a RelationshipManager's schema
    #
    ##########################################################################

    
    def buildRelations(self):
        """build our relations based on the schema defined in _relations"""
        if not getattr(self, "_relations", False): return
        for name, schema in self._relations:
            self._setObject(name, schema.createRelation(name))

        
    def lookupSchema(cls, relname):
        """
        Lookup the schema definition for a relationship. 
        All base classes are checked until RelationshipManager is found.
        """
        for name, schema in cls._relations:
            if name == relname: return schema
        raise ZenSchemaError("Schema for relation %s not found on %s" %
                                (relname, cls.__name__))
    lookupSchema = classmethod(lookupSchema)

    
    def getRelationships(self):
        """Returns a dictionary of relationship objects keyed by their names"""
        return self.objectValues(spec=RELMETATYPES)


    def getRelationshipNames(self):
        """Return our relationship names"""
        return self.objectIds(spec=RELMETATYPES)


    def checkRelations(self, repair=False, log=None):
        """Confirm the integrity of all relations on this object"""
        for rel in self.getRelationships():
            rel.checkRelation(repair, log)
                
    
    ##########################################################################
    #
    # Methods called from UI code.
    #
    ##########################################################################

    security.declareProtected('Manage Relations', 'manage_addRelation')
    def manage_addRelation(self, name, obj, REQUEST=None):
        """make a relationship"""
        self.addRelation(name, obj)
        if REQUEST: return self.callZenScreen(REQUEST)
            

    security.declareProtected('Manage Relations', 'manage_removeRelation')
    def manage_removeRelation(self, name, id=None, REQUEST=None):
        """remove a relationship to be called from UI"""
        rel = getattr(self, name, None)
        if rel == None: 
            raise AttributeError("Relationship %s, not found" % name)
        rel._delObject(id)
        if REQUEST: return self.callZenScreen(REQUEST)


    def manage_workspace(self, REQUEST):
        """return the workspace of the related object using its primary path"""
        url = REQUEST['URL']
        myp = self.getPrimaryUrlPath()
        if url.find(myp) > 0:
            Tabs.manage_workspace(self, REQUEST)
        else:    
            raise "Redirect", (myp+'/manage_workspace')


    
InitializeClass(RelationshipManager)
