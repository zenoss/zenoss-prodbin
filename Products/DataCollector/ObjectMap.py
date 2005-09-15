#################################################################
#
#   Copyright (c) 2003 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__ = """ObjectMap

ObjectMap holds the information needed to build an object in zope
basically this is a class name and a dictionary with a list of  
attributes and their values.

$Id: ObjectMap.py,v 1.2 2003/09/25 15:04:19 edahl Exp $"""

__version__ = '$Revision: 1.2 $'[11:-2]

from UserDict import UserDict

class ObjectMap(UserDict):

    def __init__(self, className):
        UserDict.__init__(self)
        self.className = className

    def getName(self):
        return self.__class__.__name__
