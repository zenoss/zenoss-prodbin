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
Common exceptions for data collectors
"""

from Products.ZenUtils.Exceptions import ZentinelException

class DataCollectorError(ZentinelException): pass

class ObjectCreationError(DataCollectorError):
    "Failed to create a related object while appling maps"
    pass

class LoginFailed(DataCollectorError):
    "Indicates a failed login to the remote device"
    pass

class CommandTimeout(DataCollectorError):
    "Full command response was not received before timeout was reached"
    pass

class StateTimeout(DataCollectorError): 
    "A timeout occured while we were waiting for some data"
    pass

class NoServerFound(DataCollectorError): 
    "No telnet or ssh server found on a machine at the given port"
    pass

class CommandNotFound(DataCollectorError): 
    "No command found to run"
    pass

class NoValidConnection(DataCollectorError):
    "No valid connection found to make"
    pass
