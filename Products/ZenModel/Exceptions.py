###############################################################
#
#   Copyright (c) 2003 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""Exceptions


$Id: Exceptions.py,v 1.2 2003/10/04 15:54:36 edahl Exp $"""

__version__ = "$Revision: 1.2 $"[11:-2]

from Products.ZenUtils.Exceptions import ZentinelException

class ZenModelError(ZentinelException): pass

class IpAddressConflict(ZenModelError): 
    """Two or more devices have the same ip"""
    pass

class IpCatalogNotFound(ZenModelError):
    """Can't find the Ip Catalog in the context passed"""
    pass

class WrongSubnetError(ZenModelError):
    pass

class DeviceExistsError(ZenModelError):
    """a device with this fqdn is already in the dmd"""
    pass

class PathNotFoundError(ZenModelError):
    """no object found in the dmd at the path given"""
    pass
