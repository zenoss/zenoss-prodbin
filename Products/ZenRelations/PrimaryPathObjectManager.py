#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""PrimaryPathObjectManager

$Id: RelationshipBase.py,v 1.26 2003/10/03 16:16:01 edahl Exp $"""

__version__ = "$Revision: 1.26 $"[11:-2]

# base classes for PrimaryPathObjectManager
from RelCopySupport import RelCopyContainer
from OFS.ObjectManager import ObjectManager
from AccessControl.Role import RoleManager
from OFS.SimpleItem import Item

from Acquisition import aq_base

class PrimaryPathObjectManager(RelCopyContainer, ObjectManager, Item):
    """
    ZenRelations adds relationships to Zope's normal containment style data
    system.  Relationships give us a networked data model as opposed to a
    simple hierarchy.  It is difficult to path through a network of objects
    so PrimaryPathObjectManager gives us a consistant hierarchical mechanism 
    for pathing to an object.  This allows our network database to pretend to
    Zope that it is really just hierarchical.  It also lets us set our
    acquisition chain to equal our primary path.  This lets us do acquistion
    within the networked database.

    The primary path of an object is maintained through the attribute
    __primary_parent__.  This is set every time an object is added to the 
    database using _setObject.
    """
    
    manage_options = ObjectManager.manage_options + Item.manage_options
        
    
    
    def getPrimaryPath(self, fromNode=None):
        """
        Return the primary path of this object by following __primary_parent__
        """
        ppath = []
        obj = aq_base(self)
        while True:
            ppath.append(obj.id) 
            parent = getattr(obj, "__primary_parent__", False)
            if not parent: break
            obj = parent
        ppath.reverse()
        basepath = getattr(obj, "zPrimaryBasePath", [])
        for i in range(len(basepath)-1,-1,-1): ppath.insert(0,basepath[i])
        try:
            idx = ppath.index(fromNode)
            ppath = ppath[idx+1:]
        except ValueError: pass
        return tuple(ppath)

    
    def getPrimaryId(self, fromNode=None):
        """Return the primary path in the form /zport/dmd/xyz"""
        pid = "/".join(self.getPrimaryPath(fromNode))
        if fromNode: pid = "/" + pid
        return pid


    def getPrimaryUrlPath(self):
        """Return the primary path as an absolute url"""
        objaq = self.primaryAq()
        return objaq.absolute_url_path()


    def primaryAq(self):
        """Return self with is acquisition path set to primary path"""
        app = self.getPhysicalRoot()
        return app.unrestrictedTraverse(self.getPrimaryPath())
       

    def getPrimaryParent(self):
        """Return our parent object by our primary path"""
        return self.__primary_parent__.primaryAq()


    def _setObject(self, id, obj, roles=None, user=None, set_owner=1):
        """Track __primary_parent__ when we are set into an object"""
        obj.__primary_parent__ = aq_base(self) 
        return ObjectManager._setObject(self, id, obj, roles, user, set_owner=1)


    def _delObject(self, id, dp=1):
        """When deleted clear __primary_parent__."""
        obj = self._getOb(id)
        ObjectManager._delObject(self, id, dp)
        obj.__primary_parent__ = None


