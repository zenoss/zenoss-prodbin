#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""SchemaManager

SchemaManager tracks the relationship schema between objects
In a ZODB.  It consists of this zope product class to which 
RelationshipSchema definitions are added and a mix in class 
that is added to classes that want to use relationships.  

$Id: SchemaManager.py,v 1.15 2003/10/03 16:16:01 edahl Exp $"""

__version__ = "$Revision: 1.15 $"[11:-2]

from OFS.ObjectManager import ObjectManager
from OFS.SimpleItem import Item
from Acquisition import Implicit
from Globals import Persistent
from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from AccessControl.Role import RoleManager
import RelationshipSchema
import string

from Products.ZenRelations.Exceptions import *

_marker = "__ZENMARKER__"

def manage_addSchemaManager(context, REQUEST = None):
                                
    """SchemaManager Factory"""
    sm = SchemaManager()
    context._setObject(sm.getId(), sm)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                    +'/manage_main')


#addSchemaManager = DTMLFile('dtml/addSchemaManager',globals())


    
class SchemaManager(ObjectManager, Implicit,
                    Persistent, RoleManager, Item):
 
    meta_type = 'Schema Manager'
   
    meta_types = ({'name':'Relationship Schema',
        'action':'manage_addProduct/RelationshipManager/addRelationshipSchema'},)
   
    manage_options = (ObjectManager.manage_options
                    +RoleManager.manage_options
                    +Item.manage_options)
    
    
    security = ClassSecurityInfo()

    def __init__(self):
        self.id = 'mySchemaManager' 
        self.title = 'Schema Manager'
        self._schema = {}

    def all_meta_types(self, interfaces = None):
        """Filter types down to only the ones we define"""
        return self.meta_types

    
    security.declareProtected('Add Relationship Schemas', 'manage_addRelSchema') 
    def manage_addRelSchema(self, rel):
        self.addRelSchema(rel)


    def _setObject(self, id, rel, roles=None, user=None, set_owner=1):
        self.addRelSchema(rel, roles, user, set_owner)


    def addRelSchema(self, rel, roles=None, user=None, set_owner=1):
        """add a new RelationshipSchema to the SchemaManager
        
        adding a schema makes two keys one for each side of
        the relationship"""
        self._addRelSchema(rel.classOne(), rel.relOne(), rel)
        self._addRelSchema(rel.classTwo(), rel.relTwo(), rel)
        ObjectManager._setObject(self, rel.id, rel, roles, user, set_owner)


    def _addRelSchema(self, myclass, relName, rel):
        if not self._schema.has_key(myclass):
            self._schema[myclass] = {}
        if self._schema[myclass].has_key(relName):
            raise SchemaError, "Relationship %s already exists" % relName
        self._schema[myclass][relName] = rel


    security.declareProtected('Add Relationship Schemas', 'manage_addRelSchema')
    def manage_removeRelSchema(self, rel):
        self.removeRelSchema(rel)

    def _delObject(self, id, dp=1):
        rel = getattr(self, id)
        self.removeRelSchema(rel, dp)
        
    def removeRelSchema(self, rel, dp=1):
        """remove RelationshipSchema from the SchemaManager"""
        self._removeRelSchema(rel.classOne(), rel.relOne())
        self._removeRelSchema(rel.classTwo(), rel.relTwo())
        ObjectManager._delObject(self, rel.id, dp)


    def _removeRelSchema(self, myclass, relName):
        del(self._schema[myclass][relName])
        if not self._schema[myclass]:
            del(self._schema[myclass])


    def getRelations(self, obj):
        """build a dictionary of relationshipschema object keyed on relname"""
        myclasses = self._getClasses(obj.__class__)
        rels = {}
        for cname in myclasses:
            if self._schema.has_key(cname):
                rcs = self._schema[cname]
                for rname, rs in rcs.items():
                    rels[rname] = rs
        return rels 

    def _getClasses(self, myclass):
        """build a list of my class names"""
        clist = []
        clist.append(myclass.__name__)
        for cs in myclass.__bases__:
            clist = clist + self._getClasses(cs)
        return clist 

           
    security.declarePublic('getRelSchema') 
    def getRelSchema(self, obj, relName):
        """lookup a RelationshipSchema by relationName

        we look for the schema object by meta_type then
        the python class hierarchy"""
        if relName:
            rel = (self._getSchemaByMeta_type(obj, relName) or
                   self._getSchemaByClass(obj.getClass(), relName))
            if not rel:
                raise SchemaError, \
                    ("No schema for class %s relation %s" % 
                    (obj.getClass().__name__, relName))
            return rel
        else:
            raise SchemaError, "No Relationship Name specified"


    def changeClass(self, rel, newName, end):
        """update the SchemaManager when a type name changes"""
        oldName = end == 1 and rel.classOne() or rel.classTwo()
        relName = end == 1 and rel.relOne() or rel.relTwo()
        if self._schema.has_key(oldName):
            del(self._schema[oldName][relName])
            if not self._schema[oldName]: del(self._schema[oldName])
            if not self._schema.has_key(newName): self._schema[newName] = {}
            self._schema[newName][relName] = rel
        else:
            raise SchemaError, "Class %s not found" % oldName
        self._p_changed = 1


    def changeRel(self, rel, relName, end):
        """update the SchemaManager when a relationship name changes"""
        cName = end == 1 and rel.classOne() or rel.classTwo()
        oldRelName = end == 1 and rel.relOne() or rel.relTwo()
        del(self._schema[cName][oldRelName])
        self._schema[cName][relName] = rel
        self._p_changed = 1


    def _getSchemaByClass(self, myclass, relName):
        """return a RelationshipSchema based on class and relationshipname
        
        look for the relationship by doing a depth first search on the 
        inheritance hierarchy.  Maybe this should use the new 2.2 search?"""
        rel = self._lookupRelSchema(myclass.__name__, relName)
        if rel: return rel
        for cl in myclass.__bases__:
            rel = self._getSchemaByClass(cl, relName)
            if rel: return rel


    def _getSchemaByMeta_type(self, obj, relName):
        if getattr(obj, 'meta_type', _marker) is not _marker:
            return self._lookupRelSchema(obj.meta_type, relName)

    
    def _lookupRelSchema(self, cName, relName):
        """lookup a RelSchema based on Class Name and RelationshipName"""
        if self._schema.has_key(cName):
            cSchema =  self._schema[cName]
            if cSchema.has_key(relName):
                return cSchema[relName]

    def loadSchemaFromFile(self, filename):
        '''Create RelationshipSchema objects based
        on the structure outlined in a csv style file'''
        file = open(filename)
        lines = map(string.rstrip, file.readlines())
        for row in lines:
            (class1, rel1,
            relType1, casc1,
            class2, rel2,
            relType2, casc2) = row.split(':')
            RelationshipSchema.manage_addRelationshipSchema(self,
                class1, rel1, relType1, class2, rel2, relType2, casc1, casc2)

InitializeClass(SchemaManager)
