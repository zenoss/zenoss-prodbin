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
# This program is part of Zenoss Core, an open source monitoring platform.
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
# For complete information please visit: http://www.zenoss.com/oss/

from Products.ZenUtils.Exceptions import ZentinelException

class ZenEventError(ZentinelException):
    """
    General problem with the event system.
    """

class ZenBackendFailure(ZenEventError):
    """MySQL or ZEO backend database connection is lost.
    """

class ZenEventNotFound(ZenEventError):
    """
    Lookkup of event failed
    """

