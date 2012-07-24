##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""RelationshipManager Errors


$Id: Exceptions.py,v 1.1 2003/10/04 15:55:17 edahl Exp $"""

__version__ = "$Revision: 1.1 $"[11:-2]

from Products.ZenUtils.Exceptions import ZentinelException

class ZenImportError(ZentinelException): pass

class ZenRelationsError(ZentinelException): pass

class ObjectNotFound(ZenRelationsError): pass

class RelationshipExistsError(ZenRelationsError):pass

class ZenSchemaError(ZenRelationsError): pass

class InvalidContainer(ZenRelationsError): 
    """
    Relationship got added to a container that isn't a RelationshipManager.
    """
    pass

zenmarker = "__ZENMARKER__"
