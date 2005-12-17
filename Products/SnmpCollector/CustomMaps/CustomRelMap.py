#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""CustomRelMap

CustomRelMap provides the interface for custom snmpcollector
objects.  These will be used to build relationship objects.

$Id: CustomRelMap.py,v 1.1 2002/06/28 22:56:35 edahl Exp $"""

__version__ = '$Revision: 1.1 $'[11:-2]

from CustomMap import CustomMap

class CustomRelMap(CustomMap):

    remoteClass = ""
    relationshipName = ""
    componentName = ""
