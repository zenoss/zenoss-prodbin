#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

"""RelTypes

Define the types of relationships

$Id: RelTypes.py,v 1.5 2002/05/31 17:40:15 edahl Exp $"""

__version__ = "$Revision: 1.5 $"[11:-2]

TO_ONE = 1
TO_MANY = 2
TO_MANY_CONT = 4  #tomany that is a container (like object manager)

# relationship types are determined by the
# addition of each side of the relationship 
ONE_TO_ONE = 2
ONE_TO_MANY = 3
MANY_TO_MANY = 4
ONE_TO_MANY_CONT = 5

MT_LIST = ('To One Relationship', 'To Many Relationship')
