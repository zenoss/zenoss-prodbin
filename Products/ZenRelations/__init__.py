#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################
__doc__="""__init__

Initialize the RelationshipManager Product

$Id: __init__.py,v 1.9 2002/12/06 14:25:57 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

from SchemaManager import SchemaManager, manage_addSchemaManager
from RelationshipSchema import RelationshipSchema
from RelationshipSchema import addRelationshipSchema,  manage_addRelationshipSchema
from RelationshipManager import RelationshipManager
from RelationshipManager import addRelationshipManager,  manage_addRelationshipManager
from ToOneRelationship import ToOneRelationship
from ToOneRelationship import addToOneRelationship,  manage_addToOneRelationship
from ToManyRelationship import ToManyRelationship
from ToManyRelationship import addToManyRelationship,  manage_addToManyRelationship

def initialize(registrar):
    registrar.registerClass(
        RelationshipManager,
        constructors = (addRelationshipManager, manage_addRelationshipManager))
    registrar.registerBaseClass(RelationshipManager)    
    registrar.registerClass(
        SchemaManager,
        constructors = (manage_addSchemaManager, ),
        icon = 'www/SchemaManager_icon.gif')
    registrar.registerClass(
        RelationshipSchema,
        constructors = (addRelationshipSchema, manage_addRelationshipSchema),
        icon = 'www/RelationshipSchema_icon.gif')
    registrar.registerClass(
        ToOneRelationship,
        constructors = (addToOneRelationship, manage_addToOneRelationship),
        icon = 'www/ToOneRelationship_icon.gif')
    registrar.registerClass(
        ToManyRelationship,
        constructors = (addToManyRelationship, manage_addToManyRelationship),
        icon = 'www/ToManyRelationship_icon.gif')
