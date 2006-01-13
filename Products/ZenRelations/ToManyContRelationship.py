#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""$Id: ToManyRelationship.py,v 1.48 2003/11/12 22:05:48 edahl Exp $"""

__version__ = "$Revision: 1.48 $"[11:-2]

import logging
log = logging.getLogger("zen.Relations")

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from Acquisition import aq_base

from ToManyRelationshipBase import ToManyRelationshipBase

from Products.ZenRelations.Exceptions import *


def manage_addToManyContRelationship(context, id, REQUEST=None):
    """factory for ToManyRelationship"""
    rel =  ToManyContRelationship(id)
    context._setObject(rel.id, rel)
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
    return rel.id 


addToManyContRelationship = DTMLFile('dtml/addToManyContRelationship',globals())


class ToManyContRelationship(ToManyRelationshipBase):
    """
    ToManyContRelationship is the ToMany side of a realtionship that 
    contains its related objects (like the normal Zope ObjectManager)
    """

    meta_type = "ToManyContRelationship"


    def __init__(self, id):
        """set our instance values"""
        self.id = id
        self._objects = {}


    def __call__(self):
        """when we are called return our related object in our aq context"""
        return [ob.__of__(self) for ob in self._objects.values()]


    def __getattr__(self, name):
        """look in the two object stores for related objects"""
        if self.__dict__.has_key("_objects"):
            objects = self.__dict__['_objects']
            if objects.has_key(name): return objects[name]
        raise AttributeError, name


    def __hasattr__(self, name):
        """check to see if we have an object by an id
        this will fail if passed a short id and object is stored
        with fullid (ie: it is related not contained)
        use hasobject to get around this issue"""
        return self._objects.has_key(name)
            
            
    def hasobject(self, obj):
        "check to see if we have this object"
        return self._objects.get(obj.id) == obj
    

    def addRelation(self, obj):
        """Override base to run manage_afterAdd like ObjectManager"""
        ToManyRelationshipBase.addRelation(self, obj)
        obj = obj.__of__(self)
        obj.manage_afterAdd(obj, self)


    def _setObject(self,id,object,roles=None,user=None,set_owner=1):
        """ObjectManager interface to add contained object."""
        object.__primary_parent__ = aq_base(self)
        self.addRelation(object)
        return object.getId()


    def manage_beforeDelete(self, item, container):
        """
        there are 4 possible states for _operation during beforeDelete
        -1 = object being deleted remove relation
        0 = copy, 1 = move, 2 = rename
        ToManyCont will propagate beforeDelete because its a container
        """
        if getattr(item, "_operation", -1) < 1: 
            self._remoteRemove()
        ToManyRelationshipBase.manage_beforeDelete(self, item, container)
        

    def _add(self,obj):
        """add an object to one side of this toMany relationship"""
        id = obj.id
        if self._objects.has_key(id):
            del self._objects[id]
        v=self._checkId(id)
        if v is not None: id=v
        self._objects[id] = aq_base(obj)
        obj = aq_base(obj).__of__(self)
        self._count=len(self._objects)
        self._p_changed = 1


    def _remove(self, obj=None):
        """remove object from our side of a relationship"""
        if obj: objs = [obj]
        else: objs = self.objectValuesAll()
        for robj in objs:
            robj.manage_beforeDelete(robj, self)
        if obj:
            id = obj.id
            if not self._objects.has_key(id):
                raise ObjectNotFound(
                    "Object with id %s not found on relation %s" % 
                    (id, self.id))
            del self._objects[id]
        else:
            self._objects = {}
        self._count=len(self._objects)
        self._p_changed = 1


    def _getOb(self, id, default=zenmarker):
        """look up in our local store and wrap in our aq_chain"""
        if self._objects.has_key(id):
            return self._objects[id].__of__(self)
        elif default == zenmarker:
            raise AttributeError, id
        return default


    def objectIds(self, spec=None):
        """only return contained objects"""
        if spec:
            if type(spec)==type('s'): spec=[spec]
            return [obj.id for obj in self._objects.values() \
                        if obj.meta_type in spec]
        return self._objects.keys()
    objectIdsAll = objectIds


    def objectValues(self, spec=None):
        """over ride to only return owned objects for many to many rel"""
        if spec:
            retval = []
            if type(spec)==type('s'): spec=[spec]
            return [ob.__of__(self) for ob in self._objects.values() \
                        if ob.meta_type in spec]
        return [ob.__of__(self) for ob in self._objects.values()]
    objectValuesAll = objectValues


    def objectValuesGen(self):
        """Generator that returns all related objects."""
        for obj in self._objects.values():
            yield obj.__of__(self)


    def objectItems(self, spec=None):
        """over ride to only return owned objects for many to many rel"""
        if spec:
            if type(spec)==type('s'): spec=[spec]
            return [(key,value.__of__(self)) \
                for (key,value) in self._objects.items() \
                    if value.meta_type in spec]
        return [(key,value.__of__(self)) \
                    for (key,value) in self._objects.items()]
    objectItemsAll = objectItems


#FIXME - need to make this work
#    def all_meta_types(self, interfaces=None):
#        mts = []
#        for mt in ToManyRelationshipBase.all_meta_types(self, interfaces):
#            if (mt.has_key('instance') and mt['instance']):
#                for cl in self.sub_classes:
#                    if checkClass(mt['instance'], cl):
#                        mts.append(mt)
#        return mts
   

    def _getCopy(self, container):
        """
        make new relation add copies of contained objs 
        and refs if the relation is a many to many
        """
        rel = self.__class__(self.id)
        rel.__primary_parent__ = container
        rel = rel.__of__(container)
        norelcopy = getattr(self, 'zNoRelationshipCopy', [])
        if self.id in norelcopy: return rel
        for oobj in self.objectValuesAll():
            cobj = oobj._getCopy(rel)
            rel._setObject(cobj.id, cobj)
        return rel    


    def exportXml(self, ofile):
        """Return an xml representation of a ToManyContRelationship
        <tomanycont id='interfaces'>
            <object id='hme0' 
                module='Products.Confmon.IpInterface' class='IpInterface'>
                <property></property> etc....
            </object>
        </tomanycont>
        """
        if self.countObjects() == 0: return
        ofile.write("<tomanycont id='%s'>\n" % self.id)
        for obj in self.objectValues():
            obj.exportXml(ofile)
        ofile.write("</tomanycont>\n")

    
    def checkRelation(self, repair=False):
        """Check to make sure that relationship bidirectionality is ok.
        """
        if repair and len(self._objects) != self._count: 
            log.warn("resetting count on %s", self.getPrimaryId()) 
            self._resetCount()


InitializeClass(ToManyContRelationship)
