#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""Exceptions

$Id: Exceptions.py,v 1.3 2003/09/25 15:04:19 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]


class DataCollectorError(Exception): pass

class ObjectCreationError(DataCollectorError):
    "failed to create a related object while appling maps"
    pass

class LoginFailed(DataCollectorError):
    "Indicates a failed login to the remote device"
    pass

class CommandTimeout(DataCollectorError):
    "full command response was not received before timeout was reached"
    pass

class StateTimeout(DataCollectorError): 
    "a timeout occured while we were waiting for some data"
    pass

class NoServerFound(DataCollectorError): 
    "no telnet or ssh server found on a machine at the given port"
    pass
