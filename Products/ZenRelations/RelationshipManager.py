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


    security.declareProtected('Manage Relations', 'manage_addRelation')
    def manage_addRelation(self, name, obj):
        """make a relationship"""
        self.addRelation(name, obj)
            

    security.declareProtected('Manage Relations', 'addRelation')
    def addRelation(self, name, obj):
        """add an object to a relationship addRelation(name, obj)
        checks schema and maintains both ends of 
        a relationship based on its cardinality"""
        rs = self.getRelSchema(name)
        self._checkSchema(name, rs, obj)
        self._add(name, obj)
        obj._add(rs.remoteAtt(name), self)


    security.declareProtected('Manage Relations', 'manage_removeRelation')
    def manage_removeRelation(self, name, obj = None):
        """remove a relationship"""
        self.removeRelation(name, obj)


    security.declareProtected('Manage Relations', 'removeRelation')
    def removeRelation(self, name, obj = None):
        """remove and object from a relationship"""
        rel = getattr(self, name, None)
        if rel == None: 
            raise AttributeError("Relationship %s, not found" % name)
        rel.removeRelation(obj)


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

        
    def manage_afterAdd(self, item, container):
        """if we have moved or our id has been changed update primaryPath
        and then update the relationship keys in all our to many relations"""
        oldppath = self.getPrimaryPath()
        if self.setPrimaryPath():
            self.notifyObjectRename(oldppath)
        RelationshipObjectManager.manage_afterAdd(self, item, self)


    def manage_afterClone(self, item):
        """cleanup after a clone of this object"""
        oldppath = self.getPrimaryPath()
        self.setPrimaryPath(force=1)
        self.notifyObjectRename(oldppath)
        RelationshipObjectManager.manage_afterClone(self, item)


    def notifyObjectRename(self, oldppath):
        """notify all remote to many rels that our name or path has changed"""
        for name in self.objectIds('To One Relationship'):
            rs = self.getRelSchema(name)
            if rs.remoteType(name) == TO_MANY: 
                rname = rs.remoteAtt(name)
                robj = getattr(self, name).obj
                if robj: robj._remoteRenameObject(self, rname, oldppath)    
        for name in self.objectIds('To Many Relationship'):
            rs = self.getRelSchema(name)
            if rs.remoteType(name) == TO_MANY: 
                rname = rs.remoteAtt(name)
                for robj in getattr(self,name).objectValuesAll():
                    robj._remoteRenameObject(self, rname, oldppath)    

    
    def _remoteRenameObject(self, robj, rname, oldppath):
        """when an object is moved or renamed this method is called from 
        the changing object on the remote object it is related to.
        it gets the relationship and calls renameObject on it."""
        rel = getattr(self, rname, None)
        if not rel: raise AttributeError("Relationship %s not found" % rname)
        rel.renameObject(robj, oldppath)

  
    def _getCopy(self, container):
        """use deepcopy to make copy of relationshipmanager toone and tomany
        make copy of relationship manager set up relations correctly"""
        id = self.id
        if getattr(container, id, _marker) is not _marker:
            id = "copy_of_" + id
        cobj = self.__class__(id) #make new instance
        cobj = cobj.__of__(container) #give the copy container's aq chain
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
