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

__doc__="""Exceptions


$Id: Exceptions.py,v 1.2 2003/10/04 15:54:36 edahl Exp $"""

__version__ = "$Revision: 1.2 $"[11:-2]

from Products.ZenUtils.Exceptions import ZentinelException

class ZenModelError(ZentinelException): pass

class IpAddressConflict(ZenModelError): 
    """Two or more devices have the same ip"""

class IpCatalogNotFound(ZenModelError):
    """Can't find the Ip Catalog in the context passed"""

class WrongSubnetError(ZenModelError):
    pass

class DeviceExistsError(ZenModelError):
    """a device with this fqdn is already in the dmd"""

class PathNotFoundError(ZenModelError):
    """no object found in the dmd at the path given"""

class TraceRouteGap(ZenModelError):
    """Missing data found during traceroute."""


class NoSnmp(ZenModelError):
    """Can't open an snmp connection to the device."""

class NoIPAddress(ZenModelError):
    """No IP Address found for device name."""
