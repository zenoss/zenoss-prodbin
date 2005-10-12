#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""$Id: ToManyRelationship.py,v 1.48 2003/11/12 22:05:48 edahl Exp $"""

__version__ = "$Revision: 1.48 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from Acquisition import aq_base

from ToManyRelationshipBase import ToManyRelationshipBase

from Products.ZenRelations.Exceptions import *


def manage_addToManyRelationship(context, id, REQUEST=None):
    """factory for ToManyRelationship"""
    rel =  ToManyRelationship(id)
    context._setObject(rel.id, rel)
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
    return rel.id 


addToManyRelationship = DTMLFile('dtml/addToManyRelationship',globals())


class ToManyRelationship(ToManyRelationshipBase):
    """
    ToManyRelationship manages the ToMany side of a bi-directional relation
    between to objects.  It does not return values for any of the object* 
    calls defined on ObjectManager so that Zope can still work with its
    containment assumptions.  It provides object*All calles that return
    its object in the same way that ObjectManager does.

    Related references are maintained in a list.
    """

    meta_type = "ToManyRelationship"


    def __init__(self, id):
        """ToManyRelationships use an array to store related objects"""
        self.id = id
        self._objects = []


    def __call__(self):
        """when we are called return our related object in our aq context"""
        return [ob.__of__(self) for ob in self._objects]


    def hasobject(self, obj):
        "check to see if we have this object"
        try:
            idx = self._objects.index(obj)
            return self._objects[idx]
        except ValueError:
            return None
            

    def manage_beforeDelete(self, item, container):
        """
        there are 4 possible states for _operation during beforeDelete
        -1 = object being deleted remove relation
        0 = copy, 1 = move, 2 = rename
        ToMany unlinks from its remote relations if its being deleted.
        ToMany will not propagate beforeDelete because its not a container.
        """
        if getattr(item, "_operation", -1) < 1: 
            self._remoteRemove()
        

    def manage_pasteObjects(self, cb_copy_data=None, REQUEST=None):
        """ToManyRelationships link instead of pasting"""
        return self.manage_linkObjects(cb_copy_data=cb_copy_data, 
                                        REQUEST=REQUEST)

        
    def _add(self,obj):
        """add an object to one side of this toMany relationship"""
        if obj in self._objects: return
        self._objects.append(aq_base(obj))
        self._p_changed = 1


    def _remove(self, obj=None):
        """remove object from our side of a relationship"""
        if obj:
            try:
                self._objects.remove(obj)
            except ValueError:
                raise ObjectNotFound(
                    "Object with id %s not found on relation %s" % 
                    (obj.id, self.id))
        else:
            self._objects = []
        self._p_changed = 1


    def _setObject(self,id,object,roles=None,user=None,set_owner=1):
        """Set and object onto a ToMany by calling addRelation"""
        self.addRelation(object)

    
    def _delObject(self, id):
        """
        Delete object by its absolute id (ie /zport/dmd/bla/bla)
        (this is sent out in the object*All API)
        """
        obj = self.unrestrictedTraverse(id)
        self.removeRelation(obj)

    
    #FIXME - if a ToMany is walked by restrictedTraverse it will fail
    #   This is a schema error for in all cases I can think of now...
    #   We should only traverse ToManyCont...
    def _getOb(self, id, default=None):
        """
        Return object by its absolute id (ie /zport/dmd/bla/bla)
        (this is sent out in the object*All API)
        """
        try:
            return self.unrestrictedTraverse(id)
        except KeyError: 
            if default != zenmarker: return default
            else: raise AttributeError(id)


    def objectIdsAll(self):
        """
        Return object ids as their absolute primaryId. 
        """
        return [obj.getPrimaryId() for obj in self._objects]
           

    def objectIds(self, spec=None):
        """
        ToManyRelationship doesn't publish objectIds to prevent 
        zope recursion problems. 
        """
        return []
             

    def objectValuesAll(self):
        """return all related object values"""
        return [ob.__of__(self) for ob in self._objects]


    def objectValues(self, spec=None):
        """
        ToManyRelationship doesn't publish objectValues to prevent 
        zope recursion problems. 
        """
        return []


    def objectItemsAll(self):
        """
        Return object items where key is primaryId.
        """
        objs = []
        for obj in self._objects:
            objs.append((obj.getPrimaryId(), obj))
        return objs
           

    def objectItems(self, spec=None):
        """
        ToManyRelationship doesn't publish objectItems to prevent 
        zope recursion problems. 
        """
        return []


    def _getCopy(self, container):
        """
        create copy and link remote objects if remote side is TO_MANY
        """
        rel = self.__class__(self.id)
        rel.__primary_parent__ = container
        norelcopy = getattr(self, 'zNoRelationshipCopy', [])
        if self.id in norelcopy: return rel
        if self.remoteTypeName() == "ToMany":
            for robj in self.objectValuesAll():
                rel.addRelation(robj)
        return rel    


    def all_meta_types(self, interfaces=None):
        """Return empty list not allowed to add objects to a ToManyRelation"""
        return []


InitializeClass(ToManyRelationship)
