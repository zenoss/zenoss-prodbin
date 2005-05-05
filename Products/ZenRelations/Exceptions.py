#################################################################
#
#   Copyright (c) 2003 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""RelationshipManager Errors


$Id: Exceptions.py,v 1.1 2003/10/04 15:55:17 edahl Exp $"""

__version__ = "$Revision: 1.1 $"[11:-2]

from Products.ZenUtils.Exceptions import ZentinelException

class RelationshipManagerError(ZentinelException): pass

class ObjectNotFound(RelationshipManagerError): pass

class RelationshipExistsError(RelationshipManagerError):pass

class SchemaError(RelationshipManagerError): pass

class InvalidContainer(RelationshipManagerError): 
    """
    Relationship got added to a container that isn't a RelationshipManager.
    """
    pass
