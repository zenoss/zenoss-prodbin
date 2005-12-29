#################################################################
#
#   Copyright (c) 2003 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__ = """RelationshipMap

RelationshipMap holds a list of ObjectMaps that can be
added to the relationship named by relationshipName.

$Id: RelationshipMap.py,v 1.2 2003/09/25 15:04:19 edahl Exp $"""

__version__ = '$Revision: 1.2 $'[11:-2]

from UserList import UserList

class RelationshipMap(UserList):
    

    def __init__(self, relationshipName, componentName=""):
        UserList.__init__(self)
        self.relationshipName = relationshipName
        # will this map to device/os/hw.
        self.componentName = componentName

    def getName(self):
        return self.__class__.__name__
