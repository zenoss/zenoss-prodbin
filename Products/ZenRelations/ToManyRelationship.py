#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""ToManyRelationship

ToManyRelationship is an ObjectManager that handles the
ToMany side of a relationship.  

$Id: ToManyRelationship.py,v 1.48 2003/11/12 22:05:48 edahl Exp $"""

__version__ = "$Revision: 1.48 $"[11:-2]

import sys

from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from Acquisition import aq_base
from App.Dialogs import MessageDialog
from App.Management import Tabs
from OFS.ObjectManager import BadRequestException, BeforeDeleteException
from OFS.ObjectManager import ObjectManager
from zLOG import LOG, ERROR

from Products.ZenUtils.Utils import checkClass

from RelationshipAlias import RelationshipAlias
from SchemaManager import SchemaError
from SchemaManager import SchemaManager
from RelationshipBase import RelationshipBase, checkContainer
from RelationshipAlias import RelationshipAlias

from RelTypes import *
from Products.ZenRelations.Exceptions import *

_marker = []

def addRel(context, rel, REQUEST = None):
    """ToManyRelationship shared context placement"""
    try:
        try:
            context._setObject(rel.id, rel)
        except AttributeError:
            raise "InvalidContainer"
    except SchemaError, e:
        if REQUEST:
            return   MessageDialog(
            title = "Relationship Schema Error",
            message = e.args[0],
            action = "manage_main")
        else:
            raise
    except "InvalidContainer":
        if REQUEST:
            return MessageDialog(
                title = "Relationship Add Error",
                message = "Must add Relationship to RelationshipManager",
                action = "manage_main")
        else:
            raise

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main')


def manage_addToManyRelationship(context, id, title = None,
                                    REQUEST = None):
    """factory for ToManyRelationship"""
    rel =  ToManyRelationship(id, title)
    return addRel(context, rel, REQUEST)


addToManyRelationship = DTMLFile('dtml/addToManyRelationship',globals())


class RelationshipExistsError(Exception):pass

class ToManyRelationship(RelationshipBase):
    """ToManyRelationship is an ObjectManager that maintains the
    To Many side of a relationship"""

    meta_type = 'To Many Relationship'
   
    security = ClassSecurityInfo()

    manage_main = DTMLFile('dtml/ToManyRelationshipMain',globals())
    
    def __init__(self, id, title = None):
        """set our instance values"""
        self.id = id
        self.title = title 
        self._ownedObjects = {}
        self._objects = {}
        self.primaryPath = [] 
        self._isManyToMany = 0


    def __call__(self, spec=None):
        """when we are called return our related object based on the spec"""
        return self.objectValuesAll(spec)


    def __getattr__(self, name):
        """look in the two object stores for related objects"""
        ownedObjects = self.__dict__['_ownedObjects']
        objects = self.__dict__['_objects']
        if self.__dict__.has_key(name):
            return self.__dict__[name]
        elif ownedObjects.has_key(name):
            return ownedObjects[name]
        elif objects.has_key(name):
            return objects[name]
        else:
            raise AttributeError, name


    def __hasattr__(self, name):
        """check to see if we have an object by an id
        this will fail if passed a short id and object is stored
        with fullid (ie: it is related not contained)
        use hasobject to get around this issue"""
        return (self.__dict__.has_key(name) or
            self._ownedObjects.has_key(name) or
            self._objects.has_key(name))
 

    def hasobject(self, obj):
        "check to see if we have this object"
        id = obj.id
        fullid = obj.getPrimaryId()
        return self._ownedObjects.has_key(id) or self._objects.has_key(fullid)
            

    def findObjectsById(self, partid):
        """find objects by id using substring"""
        objects = []
        for fullid in self.objectIdsAll():
            if fullid.find(partid) > -1:
                objects.append(self._getOb(fullid))
        return objects 


    def countObjects(self):
        """get the number of objects in this relationship"""
        return len(self._objects) + len(self._ownedObjects)

    
    def all_meta_types(self, interfaces=None):
        if not hasattr(aq_base(self), 'sub_classes'):
            rs = self.getRelSchema(self.id)
            self.sub_classes = (rs.remoteClass(self.id),)

        mts = []
        for mt in RelationshipBase.all_meta_types(self, interfaces):
            if (mt.has_key('instance') and mt['instance']):
                for cl in self.sub_classes:
                    if checkClass(mt['instance'], cl):
                        mts.append(mt)
        return mts


    def getClass(self):
        """get our parent from primary path and return its class"""
        return self.getParent().__class__

    def manage_workspace(self, REQUEST):
        """if this has been called on us return our workspace
        if not redirect to the workspace of a related object"""
        id = REQUEST['URL'].split('/')[-2]
        if id == self.id:
            Tabs.manage_workspace(self, REQUEST) 
        else:    
            obj = self._getOb(self, id)
            raise "Redirect", (REQUEST['BASE0']+ obj.getPrimaryUrlPath()
                                        +'/manage_workspace')


    def manage_afterAdd(self, item, container):
        """check to see if we are being added to a valid relmanager
        set our parent class and call subobjects"""
        self._relClass = container.__class__
        checkContainer(container)
        if hasattr(self, 'mySchemaManager'):
            rs = self.getRelSchema(self.id)
            self._isManyToMany = rs.isManyToMany()
        ObjectManager.manage_afterAdd(self, item, self)


    security.declareProtected('Manage Relations', 'addRelation')
    def addRelation(self, obj,id=None,owned=0,roles=None,user=None,set_owner=1):
        """work of building relationship done here
        checks schema and maintains both ends of 
        a relationship based on its cardinality"""
        if not owned and (not id or id.find('/') != 0):
            id = obj.getPrimaryId()
        elif not id:
            id = obj.id
        name = self.id
        rel = self.getRelSchema(name)
        self._checkSchema(name, rel, obj)
        self._addToMany(obj, id, owned, roles, user, set_owner)
        obj = getattr(self, id)
        if rel.remoteType(name) == TO_ONE:
            obj._addToOne(rel.remoteAtt(name), self.aq_parent)
        elif rel.remoteType(name) == TO_MANY:
            obj._addToMany(rel.remoteAtt(name), self.aq_parent)


    security.declareProtected('Manage Relations', 'removeRelation')
    def removeRelation(self, obj=None, id=None):
        """remove and object from a relationship"""
        if not obj and not id:
            for obj in self.objectValuesAll():
                self._removeRemoteRelation(obj)
            self._removeToMany()
        else:
            if not obj: obj = self._getOb(id)
            self._removeRemoteRelation(obj)
            self._removeToMany(obj)


    def _removeRemoteRelation(self, obj=None):
        name = self.id
        rel = self.getRelSchema(name)
        if rel.remoteType(name) == TO_ONE:
            obj._removeToOne(rel.remoteAtt(name))
        elif rel.remoteType(name) == TO_MANY:
            obj._removeToMany(rel.remoteAtt(name), self.aq_parent)

    
    security.declareProtected('Manage Relations', 'renameId')
    def renameId(self, obj):
        """change an objects id in its related collection"""
        nid = obj.id
        nfullid = obj.getPrimaryId()
        oldid = obj.oldid
        oldfullid = nfullid.split('/')[:-1]
        oldfullid.append(oldid)
        oldfullid = '/'.join(oldfullid)
        if self._ownedObjects.has_key(oldid):
            objstore = self._ownedObjects
        elif self._objects.has_key(oldfullid):
            objstore = self._objects
            oldid = oldfullid
            nid = nfullid
        else:
            raise ObjectNotFound, \
                "old id %s not found in relation %s on object %s" % (
                            oldid, self.id, self.aq_parent.id)
        tobj = objstore[oldid]
        del objstore[oldid]
        objstore[nid] = tobj
        self._p_changed = 1


    def _addToMany(self,obj,id=None,owned=0,roles=None,user=None,set_owner=1):
        """add an object to one side of this toMany relationship"""
        if not owned and (not id or id.find('/') != 0):
            id = obj.getPrimaryId()
        elif not id:
            id = obj.id
        if ((self._ownedObjects.has_key(id) and owned) or
            (self._objects.has_key(id) and not owned)): return
        elif self._objects.has_key(id) and owned: 
            del self._objects[id]
        elif self._ownedObjects.has_key(id) and not owned:
            del self._ownedObjects[id]
        if id.find('/') != 0:
            v=self._checkId(id)
            if v is not None: id=v
        if owned:
            self._ownedObjects[id] = obj
            obj = self._getOb(id)
            obj.manage_afterAdd(obj, self)
        else:    
            self._objects[id] = obj
        self._p_changed = 1


    def _setObject(self,id,object,roles=None,user=None,set_owner=1):
        """set relationship and mark object as owned"""
        self.addRelation(object,id,owned=1,roles=roles,user=user,
                            set_owner=set_owner)
        return object.getId()


    def _removeToMany(self, obj=None, id=None):
        """remove object from one side of a tomany relationship"""
        if obj or id: 
            fullid = ""
            if obj: fullid = obj.getPrimaryId()
            if not id: id = obj.getId()
            if self._ownedObjects.has_key(id):
                self._ownedDelObject(id)
            elif self._objects.has_key(fullid):    
                del self._objects[fullid]
        else:
            for id in self.objectIdsOwned():
                self._ownedDelObject(id)
            self._objects = {}
            self._ownedObject = {}
        self._p_changed = 1

    
    def _ownedDelObject(self, id):
        """proper protocol for owned object deletion (as per ObjectManager)"""
        object=self._getOb(id)
        try:
            object.manage_beforeDelete(object, self)
        except BeforeDeleteException, ob:
            raise
        except:
            LOG('Zope',ERROR,'manage_beforeDelete() threw',
                error=sys.exc_info())
            pass 
        # the object may be gone because it got cleaned 
        # up in manage_beforeDelete NOT SURE ABOUT THIS!!!!
        if self._ownedObjects.has_key(id):
            del self._ownedObjects[id]


    def _delObject(self, id, dp=1):
        """unlink relationship (both sides) and remove from owned"""
        self.removeRelation(id=id)


    def _setOb(self, id, obj): 
        """don't use attributes in relations"""
        pass
        
  
    def _delOb(self, id):
        """don't use attributes in relations"""
        pass


    def _getOb(self, id, default=[]):
        """look up in our local store and wrap in our aq_chain"""
        if self._ownedObjects.has_key(id):
            return self._ownedObjects[id].__of__(self)
        elif self._objects.has_key(id):
            return self._objects[id].__of__(self)
        elif default == []:
            raise AttributeError, id
        else:
            return default


    def _objectIds(self, ids, spec=None):
        """do work of getting ids and filter if nessesary"""
        if spec is not None:
            retval = []
            if type(spec)==type('s'):
                spec=[spec]
            for id in ids:
                ob = self._getOb(id)
                if ob.meta_type in spec:
                    retval.append(id)
            return retval
        return ids


    def _objectValues(self, objects, spec=None):
        """do work of getting values and filter if nessesary"""
        if spec:
            retval = []
            if type(spec)==type('s'):
                spec=[spec]
            return [ob.__of__(self) for ob in objects if ob.meta_type in spec]
        return [ob.__of__(self) for ob in objects]


    def _objectItems(self, items, spec=None):
        """do work of getting items and filter if nessesary"""
        if spec:
            if type(spec)==type('s'):
                spec=[spec]
            return [(key,value.__of__(self)) for (key,value) in items \
                if value.meta_type in spec]
        return [(key,value.__of__(self)) for (key,value) in items]


    security.declareProtected('View', 'objectIdsAll')
    def objectIdsAll(self, spec=None):
        """return all object ids even if we are a many to many"""
        return self._objectIds(self._ownedObjects.keys()
                            + self._objects.keys(), spec)


    security.declareProtected('View', 'objectValuesAll')
    def objectValuesAll(self, spec=None):
        """return all values even if we are a many to many """
        return self._objectValues(self._ownedObjects.values()
                            + self._objects.values(), spec)


    security.declareProtected('View', 'objectItemsAll')
    def objectItemsAll(self, spec=None):
        """return all Items even if we are a many to many """
        return self._objectItems(self._ownedObjects.items()
                            + self._objects.items(), spec)


    #security.declareProtected('View', 'objectMapAll')
    #def objectMapAll(self):
    #    """map all values even if we are a many to many """
    #    return tuple(map(lambda dict: dict.copy(), self._objects))


    security.declareProtected('View', 'objectIdsOwned')
    def objectIdsOwned(self, spec=None):
        """return only owned object ids"""
        return self._objectIds(self._ownedObjects.keys(), spec)


    security.declareProtected('View', 'objectValuesOwned')
    def objectValuesOwned(self, spec=None):
        """return only owned object values"""
        return self._objectValues(self._ownedObjects.values(), spec)


    security.declareProtected('View', 'objectItemsOwned')
    def objectItemsOnwed(self, spec=None):
        """return only owned object items"""
        return self._objectItems(self._ownedObjects.items(), spec)


    def objectIds(self, spec=None):
        """over ride to only return owned objects for many to many rel"""
        objects = self._ownedObjects.keys()
        if not self._isManyToMany:
            objects += self._objects.keys()
        return self._objectIds(objects, spec)
             

    def objectValues(self, spec=None):
        """over ride to only return owned objects for many to many rel"""
        objects = self._ownedObjects.values()
        if not self._isManyToMany:
            objects += self._objects.values()
        return self._objectValues(objects, spec)


    def objectItems(self, spec=None):
        """over ride to only return owned objects for many to many rel"""
        objects = self._ownedObjects.items()
        if not self._isManyToMany:
            objects += self._objects.items()
        return self._objectItems(objects, spec)


    #def objectMap(self):
    #    """over ride to only return owned objects for many to many rel"""
    #    if self._isManyToMany:
    #        return tuple(map(lambda dict: dict.copy(), self._ownedObjects))
    #    else:    
    #        return self.objectMapAll()


    def objectValuesLinked(self, spec=None):
        objects = self._objects.values()
        return self._objectValues(objects, spec)


    def _getCopy(self, container):
        """make new relation add copies of owned objs 
        and refs if many to many"""
        name = self.id
        rel = self.__class__(name)
        rel = rel.__of__(container)
        norelcopy = getattr(self, 'noRelationshipCopy', [])
        if name in norelcopy: return rel
        for oobj in self.objectValuesOwned():
            cobj = oobj._getCopy(rel)
            rel._setObject(cobj.id, cobj)
        rs = self.getRelSchema(name)
        if self._isManyToMany:
            for robj in self._objects.values():
                if not rel._getOb(robj.getPrimaryId(), None):
                    container.addRelation(name, robj)
        return rel    
  

    def rebuildKeys(self, log=None):
        """rebuild the keys stored in this tomany's remote relations"""
        changed = 0
        for key, obj in self._objects.items():
            curkey = obj.getPrimaryId()
            if key != curkey:
                if log: log.warn("fixing key %s should be %s" % (key, curkey))
                del self._objects[key]
                self._objects[curkey] = obj
                if self._getOb(curkey, None): self._delOb(curkey)
                changed = 1
        self._p_changed = changed
        return changed



    def exportXml(self):
        """return an xml representation of a ToManyRelationship
        there are two types of values in a tomany those that are
        "owned" by the relationship and those that are linked to it.
        For Owned objects we export a full object definition
        (since this is the only place the object is defined).

        <tomany id='interfaces'>
            <object id='/Devices/Servers/Windows/dhcp160.confmon.loc/hme0' 
                class='Products.Confmon.IpInterface'>
                <property></property> etc....
            </object>
            <link>/Systems/OOL/Mail</link>
        </tomany>
        """
        if not self.countObjects(): return "" 
        xml = []
        xml.append("<tomany id='%s'>" % self.id)
        for obj in self.objectValuesOwned():
            xml.append(obj.exportXml())
        
        for obj in self.objectValuesLinked():
            xml.append("<link>%s</link>" % obj.getPrimaryId())
        xml.append("</tomany>")
        return "\n".join(xml)
            


InitializeClass(ToManyRelationship)
