#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################
__doc__="""__init__

Initialize the RelationshipManager Product

$Id: __init__.py,v 1.9 2002/12/06 14:25:57 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

from RelationshipManager import RelationshipManager, addRelationshipManager, \
                                manage_addRelationshipManager
from ToOneRelationship import ToOneRelationship, addToOneRelationship, \
                                manage_addToOneRelationship
from ToManyRelationship import ToManyRelationship, addToManyRelationship, \
                                manage_addToManyRelationship
from ToManyContRelationship import ToManyContRelationship, \
                                addToManyContRelationship, \
                                manage_addToManyContRelationship

def initialize(registrar):
    registrar.registerClass(
        RelationshipManager,
        constructors = (addRelationshipManager, manage_addRelationshipManager))
    registrar.registerBaseClass(RelationshipManager)    
    registrar.registerClass(
        ToOneRelationship,
        constructors = (addToOneRelationship, manage_addToOneRelationship),
        icon = 'www/ToOneRelationship_icon.gif')
    registrar.registerClass(
        ToManyRelationship,
        constructors = (addToManyRelationship, manage_addToManyRelationship),
        icon = 'www/ToManyRelationship_icon.gif')
    registrar.registerClass(
        ToManyContRelationship,
        constructors = (addToManyContRelationship, 
                        manage_addToManyContRelationship),
        icon = 'www/ToManyContRelationship_icon.gif')
