#################################################################
#
#   Copyright (c) 2005 Zenoss, Inc. All rights reserved.
#
#################################################################


__doc__="""$Id: ToManyRelationship.py,v 1.48 2003/11/12 22:05:48 edahl Exp $"""

__version__ = "$Revision: 1.48 $"[11:-2]

# Base classes for ToManyRelationshipBase
from PrimaryPathObjectManager import PrimaryPathObjectManager
from RelationshipBase import RelationshipBase

from Globals import DTMLFile
from Acquisition import aq_base, aq_parent
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from App.Management import Tabs

from Products.ZenRelations.Exceptions import zenmarker

class ToManyRelationshipBase(PrimaryPathObjectManager, RelationshipBase):
    """
    Abstract base class for all ToMany relationships.
    """

    security = ClassSecurityInfo()

    manage_main = DTMLFile('dtml/ToManyRelationshipMain',globals())

    _operation = -1 # if a Relationship's are only deleted

    _count = 0

    def countObjects(self):
        """Return the number of objects in this relationship"""
        return self._count

   
    def _resetCount(self):
        """Reset the count of the total objects in this relation.
        """
        self._count = len(self._objects)


    def findObjectsById(self, partid):
        """Return a list of objects by running find on their id"""
        objects = []
        for id, obj in self.objectItemsAll():
            if id.find(partid) > -1:
                objects.append(obj)
        return objects 

    
    def _delObject(self, id, dp=1):
        """Emulate ObjectManager deletetion."""
        obj = self._getOb(id)
        self.removeRelation(obj)

    
    def _setOb(self, id, obj): 
        """don't use attributes in relations"""
        pass
        
  
    def _delOb(self, id):
        """don't use attributes in relations"""
        pass


    def _getOb(self, id, default=zenmarker):
        """
        Return object by id if it exists on this relationship.
        If it doesn't exist return default or if default is not set 
        raise AttributeError
        """
        raise NotImplementedError


    def manage_workspace(self, REQUEST):
        """if this has been called on us return our workspace
        if not redirect to the workspace of a related object"""
        id = REQUEST['URL'].split('/')[-2]
        if id == self.id:
            Tabs.manage_workspace(self, REQUEST) 
        else:    
            obj = self._getOb(self, id)
            raise "Redirect", (obj.getPrimaryUrlPath()+'/manage_workspace')
                                        

InitializeClass(ToManyRelationshipBase)
