###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

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

