###############################################################
#
#   Copyright (c) 2003 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""Exceptions


$Id: Exceptions.py,v 1.2 2003/10/04 15:54:36 edahl Exp $"""

__version__ = "$Revision: 1.2 $"[11:-2]


class ConfmonError(Exception): pass

class IpAddressConflict(ConfmonError): 
    """Two or more devices have the same ip"""
    pass

class IpCatalogNotFound(ConfmonError):
    """Can't find the Ip Catalog in the context passed"""
    pass

class WrongSubnetError(ConfmonError):
    pass

class DeviceExistsError(ConfmonError):
    """a device with this fqdn is already in the dmd"""
    pass

class PathNotFoundError(ConfmonError):
    """no object found in the dmd at the path given"""
    pass
