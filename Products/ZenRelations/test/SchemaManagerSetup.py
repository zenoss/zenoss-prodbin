#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""SchemaManagerSetup

Setup a schema for other tests to use

$Id: SchemaManagerSetup.py,v 1.11 2003/10/21 17:22:58 edahl Exp $"""

__version__ = "$Revision: 1.11 $"[11:-2]


from OFS.SimpleItem import Item
from OFS.Folder import manage_addFolder
from Products.ZenRelations.RelationshipManager import RelationshipManager
from Products.ZenRelations.RelationshipSchema import RelationshipSchema
from Products.ZenRelations.RelTypes import *
from Products.ZenRelations.SchemaManager import manage_addSchemaManager

MT_TYPE = 'mt'
RM_TYPE = 'rm'
class C1(RelationshipManager):
    meta_type = RM_TYPE
    all_meta_types = \
                ( { 'name'        : MT_TYPE
                  , 'action'      : 'manage_addRelaionshipManager'
                  , 'permission'  : 'Add RelationshipManagers'
                  },)

class MT(RelationshipManager):
    meta_type = MT_TYPE
    all_meta_types = \
                ( { 'name'        : RM_TYPE
                  , 'action'      : 'manage_addRelaionshipManager'
                  , 'permission'  : 'Add RelationshipManagers'
                  },)

class NORM(Item):
    def __init__(self, id):
        self.id = id

class C2(C1): pass

from OFS.PropertyManager import PropertyManager
class C3(C2, NORM, PropertyManager): 
    _properties = (
        {'id':'pingStatus', 'type':'int', 
                    'mode':'w', 'setter':'setPingStatus'},)

class SchemaManagerSetup:
    #class C1 rels
    c1 = 'C1'
    oto1 = "oto1"
    otm1 = 'otm1'
    mtm1 = 'mtm1'
    
    #class MT rels
    mt = 'MT'
    oto2 = "oto2"
    otm2 = "otm2"
    
    #class C3 rels
    c3 = 'C3'
    mtm2 = "mtm2"
   
    def setUp(self):
        manage_addSchemaManager(self.app)
        # one to one
        self.rsoto = RelationshipSchema(self.c1, self.oto1, TO_ONE,
                                        self.mt, self.oto2, TO_ONE, 1, 0)
        # one to many
        self.rsotm = RelationshipSchema(self.c1, self.otm1, TO_ONE, 
                                        MT_TYPE, self.otm2, TO_MANY)
        # many to many
        self.rsmtm = RelationshipSchema(self.c1, self.mtm1, TO_MANY,
                                        self.c3, self.mtm2, TO_MANY, 1, 0)


        self.ic1 = C1('ic1')
        self.app._setObject(self.ic1.id, self.ic1, set_owner=1)
        self.ic12 = C1('ic12')
        self.app._setObject(self.ic12.id, self.ic12)
        self.imt = MT('imt')
        self.app._setObject(self.imt.id, self.imt)
        self.imt2 = MT('imt2')
        self.app._setObject(self.imt2.id, self.imt2)
        self.imt2 = MT('imt3')
        self.ic3 = C3('ic3')
        self.app._setObject(self.ic3.id, self.ic3)
        self.ic32 = C3('ic32')
        self.app._setObject(self.ic32.id, self.ic32)
        self.ic33 = C3('ic33')
        self.inorm = NORM('inorm')
        self.app._setObject(self.inorm.id, self.inorm)
        manage_addFolder( self.app, 'folder' )
        self.folder = getattr(self.app, 'folder')
        self.folder.all_meta_types = \
                    ( 
                    { 'name'        : MT_TYPE
                      , 'action'      : 'manage_addRelaionshipManager'
                      , 'permission'  : 'Add RelationshipManagers'
                      }
                    ,
                    { 'name'        : RM_TYPE
                      , 'action'      : 'manage_addRelaionshipManager'
                      , 'permission'  : 'Add RelationshipManagers'
                      }
                    ,
                    )
        self.fc3 = C3('fc3')
        self.app.folder._setObject(self.fc3.id, self.fc3)




        get_transaction().commit()

    def tearDown(self):
        del self.ic1
        del self.imt
        del self.ic3
        del self.inorm
