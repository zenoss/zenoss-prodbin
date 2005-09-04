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


from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from Acquisition import aq_base, aq_parent
from App.Dialogs import MessageDialog
from App.Management import Tabs
from zLOG import LOG, ERROR

from Products.ZenUtils.Utils import checkClass

from SchemaManager import SchemaError
from RelationshipBase import RelationshipObjectManager

from RelTypes import *
from Products.ZenRelations.Exceptions import *

from Products.ZenUtils.Exceptions import ZentinelException

class RelationshipExistsError(ZentinelException):pass


_marker = "__ZENMARKER__"


def manage_addToManyRelationship(context, id, REQUEST=None):
    """factory for ToManyRelationship"""
    try:
        rel =  ToManyRelationship(id)
        context._setObject(rel.id, rel)
    except SchemaError, e:
        if REQUEST:
            return   MessageDialog(
            title = "Relationship Schema Error",
            message = e.args[0],
            action = "manage_main")
        raise
    except InvalidContainer:
        if REQUEST:
            return MessageDialog(
                title = "Relationship Add Error",
                message = "Must add Relationship to RelationshipManager",
                action = "manage_main")
        raise
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
    return rel.id 


addToManyRelationship = DTMLFile('dtml/addToManyRelationship',globals())



class ToManyRelationship(RelationshipObjectManager):
    """ToManyRelationship is an ObjectManager that maintains the
    To Many side of a relationship"""

    meta_type = 'To Many Relationship'
   
    security = ClassSecurityInfo()

    manage_main = DTMLFile('dtml/ToManyRelationshipMain',globals())
    
    def __init__(self, id):
        """set our instance values"""
        self.id = id
        self._objects = {}
        self.primaryPath = [] 
        self.isContainer = 0


    def __call__(self, spec=None):
        """when we are called return our related object based on the spec"""
        return self.objectValuesAll(spec)


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
        id = obj.id
        if not self.isContainer: id = obj.getPrimaryId()
        return self._objects.get(id) == obj
            

    def findObjectsById(self, partid):
        """find objects by id using substring"""
        objects = []
        for fullid in self.objectIdsAll():
            if fullid.find(partid) > -1:
                objects.append(self._getOb(fullid))
        return objects 


    def countObjects(self):
        """get the number of objects in this relationship"""
        return len(self._objects)

    
    def all_meta_types(self, interfaces=None):
        if not getattr(aq_base(self), 'sub_classes', _marker) is not _marker:
            rs = self.getRelSchema(self.id)
            self.sub_classes = (rs.remoteClass(self.id),)
        mts = []
        for mt in RelationshipObjectManager.all_meta_types(self, interfaces):
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
        if not getattr(container, "getRelSchema", False):
            raise InvalidContainer, \
                "Container %s is not a RelatioshipManager" % container.id
        rs = container.getRelSchema(self.id)
        self.isContainer = rs.relType(self.id) == TO_MANY_CONT
        if self.isContainer:
            RelationshipObjectManager.manage_afterAdd(self, item, self)


    def manage_beforeDelete(self, item, container):
        """if relationship is being deleted remove the remote side"""
        self._remoteRemove()
        if self.isContainer:
            RelationshipObjectManager.manage_beforeDelete(self, item, container)
        

    security.declareProtected('Manage Relations', 'addRelation')
    def addRelation(self, obj,id=None):
        """work of building relationship done here
        checks schema and maintains both ends of 
        a relationship based on its cardinality"""
        name = self.id
        rs = self.getRelSchema(name)
        self._checkSchema(name, rs, obj)
        self._add(obj, id)
        obj = obj.__of__(self)
        obj._add(rs.remoteAtt(name), aq_parent(self))


    def _setObject(self,id,object,roles=None,user=None,set_owner=1):
        """old ObjectManager interface to add contained object."""
        self.addRelation(object,id)
        return object.getId()


    security.declareProtected('Manage Relations', 'removeRelation')
    def removeRelation(self, obj=None):
        """remove and object from a relationship"""
        self._remoteRemove(obj)
        self._remove(obj)


    def _delObject(self, id, dp=1):
        """Emulate ObjectManager deletetion."""
        obj = self._getOb(id)
        if self.isContainer:
            obj.manage_beforeDelete(obj, self)
        self.removeRelation(obj)

    
    security.declareProtected('Manage Relations', 'renameObject')
    def renameObject(self, obj, oldppath):
        """change an objects id in its related collection"""
        if self.isContainer:
            oldid = oldppath[-1]
            newid = obj.id
        else:    
            oldid = "/".join(oldppath)  
            newid = obj.getPrimaryId()
        if self._objects.has_key(oldid):
            del self._objects[oldid]
            self._objects[newid] = aq_base(obj)
            self._p_changed = 1
        else:
            raise ObjectNotFound, \
                "old id %s not found in relation %s on object %s" % (
                            oldid, self.id, aq_parent(self).id)


    def _add(self,obj,id=None):
        """add an object to one side of this toMany relationship"""
        id = obj.id
        if not self.isContainer: id = obj.getPrimaryId()
        if self._objects.has_key(id):
            del self._objects[id]
        if id.find('/') != 0:
            v=self._checkId(id)
            if v is not None: id=v
        self._objects[id] = aq_base(obj)
        if self.isContainer:
            obj = obj.__of__(self)
            obj.manage_afterAdd(obj, self)
        self._p_changed = 1


    def _remove(self, obj=None):
        """remove object from our side of a relationship"""
        if obj:
            id = obj.id
            if not self.isContainer: id = obj.getPrimaryId()
            del self._objects[id]
        else:
            if self.isContainer:
                for obj in self.objectValuesOwned():
                    obj.manage_beforeDelete(obj, self)
            self._objects = {}
        self._p_changed = 1


    def _remoteRemove(self, obj=None):
        """remove an object from the far side of this relationship
        if no object is passed in remove all objects"""
        rs = self.getRelSchema(self.id)
        if obj: objs = [obj]
        else: objs = self.objectValuesAll()
        parent = aq_parent(self)
        rematt = rs.remoteAtt(self.id)
        for obj in objs:
            obj._remove(rematt, parent)
   

    def _setOb(self, id, obj): 
        """don't use attributes in relations"""
        pass
        
  
    def _delOb(self, id):
        """don't use attributes in relations"""
        pass


    def _getOb(self, id, default=_marker):
        """look up in our local store and wrap in our aq_chain"""
        if self._objects.has_key(id):
            return self._objects[id].__of__(self)
        elif default == _marker:
            raise AttributeError, id
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
        return self._objectIds(self._objects.keys(), spec)
                            


    security.declareProtected('View', 'objectValuesAll')
    def objectValuesAll(self, spec=None):
        """return all values even if we are a many to many """
        return self._objectValues(self._objects.values(), spec)


    security.declareProtected('View', 'objectItemsAll')
    def objectItemsAll(self, spec=None):
        """return all Items even if we are a many to many """
        return self._objectItems(self._objects.items(), spec)


    security.declareProtected('View', 'objectIdsOwned')
    def objectIdsOwned(self, spec=None):
        """return only owned object ids"""
        return self._objectIds(self._objects.keys(), spec)


    security.declareProtected('View', 'objectValuesOwned')
    def objectValuesOwned(self, spec=None):
        """return only owned object values"""
        return self._objectValues(self._objects.values(), spec)


    security.declareProtected('View', 'objectItemsOwned')
    def objectItemsOnwed(self, spec=None):
        """return only owned object items"""
        return self._objectItems(self._objects.items(), spec)


    def objectIds(self, spec=None):
        """only return contained objects"""
        if self.isContainer:
            return self._objectIds(self._object.keys(), spec)
        return []    
             

    def objectValues(self, spec=None):
        """over ride to only return owned objects for many to many rel"""
        if self.isContainer:
            return self._objectValues(self._objects.values(), spec)
        return []


    def objectItems(self, spec=None):
        """over ride to only return owned objects for many to many rel"""
        if self.isContainer:
            return self._objectItems(self._objects.items(), spec)
        return [(None, None)]


    def _getCopy(self, container):
        """make new relation add copies of contained objs 
        and refs if the relation is a many to many"""
        name = self.id
        rel = self.__class__(name)
        rel = rel.__of__(container)
        norelcopy = getattr(self, 'noRelationshipCopy', [])
        if name in norelcopy: return rel
        if self.isContainer:
            for oobj in self.objectValuesAll():
                cobj = oobj._getCopy(rel)
                rel._setObject(cobj.id, cobj)
        elif self.getRelSchema(name).remoteType(name) == TO_MANY:
            for robj in self.objectValuesAll():
                rel.addRelation(robj)
        return rel    
  

    def checkRelation(self, repair=False, log=None):
        rs = self.getRelSchema(self.id)
        ratt = rs.remoteAtt(self.id)
        for key, obj in self._objects.items():
            # if the key doesn't == the primary id fix it
            objid = obj.id
            if not self.isContainer:    
                objid = obj.getPrimaryId()
            if objid != key:
                if log: log.critical("id %s and key %s not the same" %
                    (objid, key))
                if repair:
                    del self._objects[key]
                    self._objects[objid] = obj
                    self._p_changed = 1
            # if the link isn't bidirectional
            rrel = getattr(obj, ratt)
            parent = aq_parent(self)
            if not rrel.hasobject(parent):
                if log: log.critical(
                    "BAD ToMany relation %s from %s to obj %s" 
                    % (self.id, parent.getPrimaryDmdId(), 
                        obj.getPrimaryDmdId()))
                if repair: 
                    goodobj = self.getDmdObj(obj.getPrimaryDmdId()) 
                    if goodobj:
                        if log: log.warn("RECONNECTING relation %s to obj %s" %
                            (self.id, goodobj.getPrimaryDmdId()))
                        del self._objects[objid]
                        self._p_changed = 1
                        parent.addRelation(self.id, goodobj)
                    else:
                        if log: log.warn(
                            "CLEARING relation %s to obj %s" %
                            (self.id, obj.getPrimaryDmdId()))
                        del self._objects[objid]
                        self._p_changed = 1
            # if the linked object doesn't exist in its primary path
            if (not self.getDmdObj(obj.getPrimaryDmdId())
                and self._objects.has_key(objid)):
                if log: log.warn(
                    "Removing object %s" % obj.getPrimaryDmdId())
                if repair: 
                    del self._objects[objid]
                    self._p_changed = 1


    #FIXME this doesn't work anymore is it useful?
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
