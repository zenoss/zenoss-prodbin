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

__doc__= """Zenoss exceptions

Some common exceptions detected by layers close to the GUI,
which can be caught by things such as dmd.error_handler()
"""


from Products.ZenUtils.Exceptions import ZentinelException

class ZenEventError(ZentinelException):
    """
    General problem with the event system.
    """

class ZenBackendFailure(ZenEventError):
    """MySQL or ZEO backend database connection is lost.
    """

class MySQLConnectionError(ZenEventError):
    """MySQL database connection is lost.
    """

class ZenEventNotFound(ZenEventError):
    """
    Lookup of event failed
    """

class pythonThresholdException(ZenEventError):
    """
    User-supplied threshold Python expression caused
    a traceback.
    """

class rpnThresholdException(ZenEventError):
    """
    User-supplied threshold RPN expression caused
    a traceback.
    """


