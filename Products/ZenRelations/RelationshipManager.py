#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""RelationshipManager

RelationshipManager is a mix in class to manage relationships
defined by the SchemaManager.  

$Id: RelationshipManager.py,v 1.41 2004/04/13 22:02:18 edahl Exp $"""

__version__ = "$Revision: 1.41 $"[11:-2]

import copy
from xml.sax.saxutils import escape

from Globals import InitializeClass
from Globals import DTMLFile
from OFS.CopySupport import CopySource
from Acquisition import aq_base
from AccessControl import ClassSecurityInfo
from App.Management import Tabs

from RelationshipBase import RelationshipObjectManager
from ToOneRelationship import ToOneRelationship
from ToManyRelationship import ToManyRelationship
from RelTypes import *

from Products.ZenRelations.Exceptions import *

_marker = "__ZENMARKER__"



def manage_addRelationshipManager(context, id, title = None,
                                    REQUEST = None):
    """Relationship factory"""
    rm =  RelationshipManager(id, title)
    context._setObject(id, rm)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main')

addRelationshipManager = DTMLFile('dtml/addRelationshipManager',globals())


class RelationshipManager(RelationshipObjectManager):
    """RelationshipManger manages relationships""" 

    meta_type = 'Relationship Manager'
   
    security = ClassSecurityInfo()


    def __init__(self, id):
        self.id = id
        self.oldid = id
        self._moving = 0
        self.primaryPath = [] 

            
    def absolute_url(self):
        aurl = RelationshipObjectManager.absolute_url(self)
        pp = self.getPhysicalPath()
        if pp != self.getPrimaryPath():
            aurl = aurl.split("/")[:-1]
            aurl.append(self.getPrimaryId()[1:])
            aurl = "/".join(aurl)
        return aurl

        
    security.declarePrivate('buildRelations')
    def buildRelations(self):
        """auto build relationship object on this RelationshipManager
        must be called after aquisition path is estabilished
        a good place is in manage_afterAdd"""
        if getattr(self, 'mySchemaManager', None) is not None:
            rses = self.mySchemaManager.getRelations(self)
            for rname, rs in rses.items():
                if not getattr(aq_base(self), rname, _marker) is not _marker:
                    if rs.relType(rname) == TO_ONE:
                        rel = ToOneRelationship(rname)
                    else:
                        rel = ToManyRelationship(rname)
                    self._setObject(rname, rel)
                

    security.declarePrivate('getRelSchema')
    def getRelSchema(self, name):
        """get schema object from SchemaManager
        
        we cache the schema object in a volitile
        hash so that we don't need to go back to 
        SchemaManager all the time."""
        return self.mySchemaManager.getRelSchema(self, name) 


    def _setObject(self, id, obj, roles=None, user=None, set_owner=1):
        """add object to RelationshipManger
        if the object is a relatioship check to see if there
        is a valid schema object for it"""
        id = RelationshipObjectManager._setObject(self, id, obj)  
        if obj.meta_type in MT_LIST:
            r = self.getRelSchema(id)
        return id


    #def __delObject(self, id, dp=1):
    #    """override to clear relationships before deleting relation"""
    #    mt = getattr(self, id).meta_type
    #    #try:
    #    if mt in MT_LIST: self.removeRelation(id)
    #    #except SchemaError:
    #    #    pass #we need to kill the object even if schema is gone 
    #    RelationshipObjectManager._delObject(self, id, dp)
   

    security.declareProtected('Manage Relations', 'manage_addRelation')
    def manage_addRelation(self, name, obj):
        """make a relationship"""
        try:
            self.addRelation(name, obj)
        except RelationshipManagerError:
            raise #put a dialog box here
            

    security.declareProtected('Manage Relations', 'addRelation')
    def addRelation(self, name, obj, id = None):
        """add an object to a relationship addRelation(name, obj)
        checks schema and maintains both ends of 
        a relationship based on its cardinality"""
        #if not id and obj: id = obj.id
        rs = self.getRelSchema(name)
        self._checkSchema(name, rs, obj)
        self._add(name, obj)
        obj._add(rs.remoteAtt(name), self)


    def relationKey(self, name, objid):
        """build a key that identifies the relation 
        between two object uniquely"""
        rel = self.getRelSchema(name)
        ratt = rel.remoteAtt(name)
        if name == rel.relOne():
            id1 = self.getPrimaryId()
            id2 = objid
            r1 = name
            r2 = ratt
        else:
            id1 = objid
            id2 = self.getPrimaryId()
            r1 = ratt
            r2 = name
        return "|".join((id1,r1,id2,r2))
        
    security.declareProtected('Manage Relations', 'manage_removeRelation')
    def manage_removeRelation(self, name, obj = None):
        """remove a relationship"""
        self.removeRelation(name, obj)


    security.declareProtected('Manage Relations', 'removeRelation')
    def removeRelation(self, name, obj = None):
        """remove and object from a relationship"""
        rs = self.getRelSchema(name)
        rel = getattr(self, name, None)
        if rel == None: return
        if not obj and rs.relType(name) == TO_ONE:
            obj = rel.obj
        if obj:
            obj._remove(rs.remoteAtt(name), self)
            rel._remove(obj)
        elif rs.relType(name) == TO_MANY:
            for obj in rel():
                obj._remove(rs.remoteAtt(name), self)
            rel._remove()


    def _add(self, name, obj):
        """add an object to one side of a relationship
        create the relationship object if it doesn't exist"""
        rel = getattr(self, name, None)
        if rel == None:
            rs = self.getRelSchema(name)
            if rs.relType(name) == TO_ONE:
                rel = ToOneRelationship(name)
            else:
                rel = ToManyRelationship(name)
            self._setObject(name, rel)
            rel = getattr(self, name)
        rel._add(obj)


    def _remove(self, name, obj=None):
        """remove one side of a relationship"""
        rel = getattr(self, name, None)
        if rel != None: rel._remove(obj)

        
    def _setId(self, newid):
        """track our old id if it is changed"""
        self.oldid = self.id
        self.id = newid
        #FIXME can we move rename code to here from manage_afterAdd???
        # and get rid of self.oldid


    def manage_afterAdd(self, item, container):
        """if our primaryPath is no longer valid we update it"""
        self.setPrimaryPath()
        if self.oldid != self.id:
            for name in self.objectIds('To One Relationship'):
                rs = self.getRelSchema(name)
                robj = getattr(self, name).obj
                self._remoteRename(name, rs, robj)    
            for name in self.objectIds('To Many Relationship'):
                rs = self.getRelSchema(name)
                for robj in getattr(self,name).objectValuesAll():
                    self._remoteRename(name, rs, robj)
            self.oldid = self.id
        RelationshipObjectManager.manage_afterAdd(self, item, self)
   
   
    def _remoteRename(self, name, rs, robj):
        """rename the id on remote objects"""
        if robj:
            if rs.remoteType(name) == TO_ONE:
                getattr(robj, rs.remoteAtt(name)).title = self.id
            else:
                rel = getattr(robj,rs.remoteAtt(name))
                rel.renameId(self)


    def manage_afterClone(self, item):
        """cleanup after a clone of this object"""
        self.setPrimaryPath(force=1)
        RelationshipObjectManager.manage_afterClone(self, item)


    def _getCopy(self, container):
        """use deepcopy to make copy of relationshipmanager toone and tomany
        make copy of relationship manager set up relations correctly"""
        id = self.id
        if getattr(container, id, _marker) is not _marker:
            id = "copy_of_" + id
        cobj = self.__class__(id) #make new instance
        cobj = cobj.__of__(container) #give the copy container's aq chain
        cobj.oldid = self.id
        cobj.setPrimaryPath() #set up the primarypath for the copy
        for sobj in self.objectValues():
            csobj = sobj._getCopy(cobj)
            if not hasattr(cobj, csobj.id):
                cobj._setObject(csobj.id, csobj)
        noprop = getattr(self, 'noPropertiesCopy', [])
        for name in self.getPropertyNames():
            if (getattr(self, name, None) != None and name not in noprop and
                hasattr(self, "_updateProperty")):
                val = getattr(self, name)
                cobj._updateProperty(name, val)
        return aq_base(cobj)
                
                

    def cb_isMoveable(self):
        """only allow move if we are being called from our primary path"""
        if (self.getPhysicalPath() == self.getPrimaryPath()):
            return 1
        else:
            return 0


    def _notifyOfCopyTo(self, container, op=0):
        """set cut/past state for use in manage_beforeDelete"""
        if op == 1: # cut/paste
            self._moving = 1
        else: # copy clear relations
            self._moving = 0


    def manage_beforeDelete(self, item, container):
        """handle cut/past vs. delete
        
        If we are being moved (cut/past) don't clear relationshp
        if we are being deleted set all relationship to None so
        that our related object don't have dangling references"""
        if self._moving == 1:
            self._moving = 0
        else:    
            #for name in self.objectIds(spec = 'To One Relationship'):
            #    self.removeRelation(name) 
            #for name in self.objectIds(spec = 'To Many Relationship'):
            #    self.removeRelation(name)
            RelationshipObjectManager.manage_beforeDelete(self, item, container)


    def manage_workspace(self, REQUEST):
        """return the workspace of the related object using its primary path"""
        url = REQUEST['URL']
        myp = self.getPrimaryUrlPath()
        if url.find(myp) > 0:
            Tabs.manage_workspace(self, REQUEST)
        else:    
            raise "Redirect", (REQUEST['BASE0']+myp+'/manage_workspace')


    def getProperties(self):
        """return a list of dictionaries that defines this objects properties"""
        if getattr(aq_base(self), '_properties', _marker) is not _marker:
            return self._properties
        return []
    

    def getPropertyNames(self):
        """return a list of all property names"""
        props = self.getProperties()
        names = []
        for prop in props:
            names.append(prop['id'])
        return names

    
    def getRelationships(self):
        """returns a dictionary of relationship objects keyed by their names"""
        if getattr(self, 'mySchemaManager', _marker) is not _marker:
            return self.mySchemaManager.getRelations(self)


    def getRelationshipNames(self):
        "return our relationship names"
        if getattr(self, 'mySchemaManager', _marker) is not _marker:
            return self.getRelationships().keys()


    def checkRelations(self, repair=False, log=None):
        """confirm the integrity of all relations on this object"""
        rels = self.objectValues(spec = 'To One Relationship')
        rels.extend(self.objectValues(spec = 'To Many Relationship'))
        for rel in rels:
            rel.checkRelation(repair, log)
                
    
InitializeClass(RelationshipManager)
