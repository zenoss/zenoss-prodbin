##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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
