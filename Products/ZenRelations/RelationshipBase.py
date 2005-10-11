#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""RelationshipBase

RelationshipBase is the base class for RelationshipManager
and ToManyRelationship.

$Id: RelationshipBase.py,v 1.26 2003/10/03 16:16:01 edahl Exp $"""

__version__ = "$Revision: 1.26 $"[11:-2]

import sys

# Base classes for RelationshipBase
from Acquisition import Implicit, aq_base
from Globals import Persistent
from OFS.SimpleItem import Item

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from Acquisition import aq_base

from Products.ZenRelations.Exceptions import *
from Products.ZenRelations.utils import importClass

class RelationshipBase(Implicit, Persistent, Item):
    """
    Abstract base class for all relationship classes.
    """

    manage_options = (
        Item.manage_options
        )


    _operation = -1 # if a Relationship's are only deleted

    def __call__(self):
        """Return the contents of this relation."""
        raise NotImplementedError

        
    def hasobject(self, obj):
        """Does this relationship relate to obj."""
        raise NotImplementedError


    def _add(self, obj):
        """Add object to local side of relationship."""
        raise NotImplementedError 


    def _remove(self,obj=None):
        """
        Remove object from local side of relationship. 
        If obj=None remove all object in the relationship
        """
        raise NotImplementedError 


    def _remoteRemove(self, obj=None):
        """Remove obj form the remote side of this relationship."""
        raise NotImplementedError 


    def addRelation(self, obj):
        """Form a bi-directional relation between self and obj."""
        if obj == None: raise ZenRelationsError("Can not add None to relation")
        if not isinstance(obj, self.remoteClass()):
            raise ZenSchemaError("%s restricted to class %s. %s is class %s" %
            (self.id, self.remoteClass.__name__, obj.id, obj.__class.__name__))
        self._add(obj)
        obj = obj.__of__(self)
        remoteRel = getattr(aq_base(obj), self.remoteName())
        remoteRel._add(self.__primary_parent__)


    def removeRelation(self, obj=None):
        """remove and object from a relationship"""
        self._remoteRemove(obj)
        self._remove(obj)
   

    def remoteType(self):
        """Return the type of the remote end of our relationship."""
        schema = self.__primary_parent__.lookupSchema(self.id)
        return schema.remoteType


    def remoteTypeName(self):
        """Return the type of the remote end of our relationship."""
        schema = self.__primary_parent__.lookupSchema(self.id)
        return schema.remoteType.__name__


    def remoteClass(self):
        """Return the class at the remote end of our relationship."""
        classdef = getattr(aq_base(self), "_v_remoteClass", None)
        if not classdef:
            schema = self.__primary_parent__.lookupSchema(self.id)
            baseModule = getattr(self, "zenRelationsBaseModule", "")
            classdef = importClass(schema.remoteClass, baseModule)
            self._v_remoteClass = classdef
        return classdef


    def remoteName(self):
        """Return the name at the remote end of our relationship."""
        schema = self.__primary_parent__.lookupSchema(self.id)
        return schema.remoteName


    def getPrimaryParent(self):
        """Return our parent object by our primary path"""
        return self.__primary_parent__.primaryAq()


    def getRelationshipManagerClass(self):
        """
        Return the local class of this relationship. For all relationshps
        this is the class of our __primary_parent___.
        """
        return self.__primary_parent__.__class__


    def cb_isCopyable(self):
        """Don't let relationships move off their managers"""        
        return 0
        
    
    def cb_isMoveable(self):
        """Don't let relationships move off their managers"""        
        return 0
   
 
    def manage_beforeDelete(self, item, container):
        """
        there are 4 possible states for _operation during beforeDelete
        -1 = object being deleted remove relation
        0 = copy, 1 = move, 2 = rename
        ToOne doesn't propagate beforeDelete because its not a container
        """
        if item._operation < 1: 
            self._remoteRemove()


InitializeClass(RelationshipBase)
