#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

"""RelationshipSchema

RelationshipSchema defines a relationship between two Classes or 
Zope meta_types.  There are three types of relationship one-to-one
one-to-many and many-to-many.    

$Id: RelationshipSchema.py,v 1.14 2002/06/25 19:57:57 edahl Exp $"""

__version__ = "$Revision: 1.14 $"[11:-2]

from Globals import Persistent
from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl.Role import RoleManager
from OFS.SimpleItem import Item
from Acquisition import Implicit
from Acquisition import aq_base
from AccessControl import ClassSecurityInfo

from RelTypes import *

def manage_addRelationshipSchema(context, classOne, relOne, relTypeOne,
                                    classTwo, relTwo, relTypeTwo,
                                    cascadeOne=0, cascadeTwo=0,
                                    REQUEST = None):
    """RelationshipSchema factory"""
    if context.meta_type == 'Schema Manager':
        rs =  RelationshipSchema(classOne, relOne, relTypeOne, 
                                    classTwo, relTwo, relTypeTwo,
                                    cascadeOne, cascadeTwo)
        context.manage_addRelSchema(rs)
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(context.absolute_url()
                                         +'/manage_main')
    else:
        raise Exception, "Must add Relationship Schema to SchemaManager"


addRelationshipSchema = DTMLFile('dtml/addRelationshipSchema',globals())

class RelationshipSchema(Implicit, Persistent, RoleManager, Item):

    meta_type = "Relationship Schema"
    
    security = ClassSecurityInfo()

    manage_editRelationshipSchemaForm = DTMLFile('dtml/manageEditRelationshipSchema',globals())
    
    manage_options = (
        ({  'label':    'Edit',
            'action':   'manage_editRelationshipSchemaForm', 
            },
            )
        +RoleManager.manage_options
        +Item.manage_options)


    def __init__(self, classOne, relOne, relTypeOne, 
                       classTwo, relTwo, relTypeTwo,
                       cascadeOne=0, cascadeTwo=0):

        self.id = self._genId(classOne, relOne, relTypeOne,
                              classTwo, relTwo, relTypeTwo)
        self._classOne = classOne
        self._relOne = relOne
        self._relTypeOne = int(relTypeOne)
        self._cascadeOne = int(cascadeOne)
        self._classTwo = classTwo
        self._relTwo = relTwo
        self._relTypeTwo = int(relTypeTwo)
        self._cascadeTwo = int(cascadeTwo)

    def manage_editRelationshipSchema(self, classOne, relOne, relTypeOne, 
                                    classTwo, relTwo, relTypeTwo,
                                    cascadeOne=0, cascadeTwo=0, 
                                    REQUEST=None):
        """Edit a schema object"""
        self.classOne(classOne)
        self.relOne(relOne)
        self.relTypeOne(relTypeOne)
        self.cascadeOne(cascadeOne)
        self.classTwo(classTwo)
        self.relTwo(relTwo)
        self.relTypeTwo(relTypeTwo)
        self.cascadeTwo(cascadeTwo)
        new_id = self._genId(classOne, relOne, relTypeOne,
                              classTwo, relTwo, relTypeTwo)
        if new_id != self.id:
            self.manage_renameObject(self.id, new_id)

        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(
                self.aq_parent.absolute_url()+'/manage_main')
   

    def _genId(self, classOne, relOne, relTypeOne,
                     classTwo, relTwo, relTypeTwo):
        return (classOne+'-'+relOne+'-'+str(relTypeOne)+
                    '-'+classTwo+'-'+relTwo+'-'+str(relTypeTwo))
        

    def classOne(self, name = None):
        if not name: return self._classOne
        if name != self._classOne:
            self.changeClass(self, name, 1)
            self._classOne = name
        
    
    def relOne(self, name = None):
        if not name: return self._relOne
        if name != self._relOne:
            self.changeRel(self, name, 1)
            self._relOne = name


    def relTypeOne(self, value = None):
        if not value: return self._relTypeOne
        self._relTypeOne = value


    def cascadeOne(self, value = None):
        if value == None: return self._cascadeOne
        self._cascadeOne = value 


    def classTwo(self, name = None):
        if not name: return self._classTwo
        if name != self._classTwo:
            self.changeClass(self, name, 2)
            self._classTwo = name


    def relTwo(self, name = None):
        if not name: return self._relTwo
        if name != self._relTwo:
            self.changeRel(self, name, 2)
            self._relTwo = name


    def relTypeTwo(self, value = None):
        if not value: return self._relTypeTwo
        self._relTypeTwo = value


    def cascadeTwo(self, value = None):
        if value == None: return self._cascadeTwo
        self._cascadeTwo = value


    def remoteAtt(self, name):
        """return the remote attribute name of a relation"""
        if name == self._relOne:
            return self._relTwo
        else:
            return self._relOne

    def remoteClass(self, name):
        """return the remote class of a relation"""
        if name == self._relOne:
            return self._classTwo
        else:
            return self._classOne

    def remoteType(self, name):
        """return the remote type of a relation"""
        if name == self._relOne:
            return self._relTypeTwo
        else:
            return self._relTypeOne
    
    def relType(self, name):
        """return the local type of a relation"""
        if name == self._relTwo:
            return self._relTypeTwo
        else:
            return self._relTypeOne
   
    def cascade(self, name):
        """return the local cascade property of a relation"""
        if name == self._relTwo:
            return self._cascadeTwo
        else:
            return self._cascadeOne


    def relationType(self):
        return self.relTypeOne() + self.relTypeTwo()


    def isManyToMany(self):
        return self.relationType() is MANY_TO_MANY


InitializeClass(RelationshipSchema)
