#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

"""Time

Utilities for consistent manipulation of Dates and Time.  All simple
code should migrate here, and without dependencies on anything other
than standard python libraries.

$Id:$"""

__version__ = "$$"[11:-2]

import time

def _maybenow(gmtSecondsSince1970):
    if gmtSecondsSince1970 is None:
        return time.time()
    return gmtSecondsSince1970

def LocalDateTime(gmtSecondsSince1970 = None):
    value = _maybenow(gmtSecondsSince1970)
    secs = value % 60
    return time.strftime("%Y/%m/%d %H:%M:%%06.3f", time.localtime(value)) % secs

def USDate(gmtSecondsSince1970 = None):
    value = _maybenow(gmtSecondsSince1970)
    return time.strftime("%m/%d/%Y", time.localtime(value))

def YYYYMMDDHHMMS(gmtSecondsSince1970 = None):
    value = _maybenow(gmtSecondsSince1970)
    return time.strftime("%Y%m%d%H%M%S", time.localtime(value))

