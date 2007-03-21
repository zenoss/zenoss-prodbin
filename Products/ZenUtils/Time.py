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
    return int(gmtSecondsSince1970)

def LocalDateTime(gmtSecondsSince1970 = None):
    value = _maybenow(gmtSecondsSince1970)
    secs = value % 60
    return time.strftime("%Y/%m/%d %H:%M:%%06.3f", time.localtime(value)) % secs

def LocalDateTimeSecsResolution(gmtSecondsSince1970 = None):
    value = _maybenow(gmtSecondsSince1970)
    return time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(value)) 

def USDate(gmtSecondsSince1970 = None):
    value = _maybenow(gmtSecondsSince1970)
    return time.strftime("%m/%d/%Y", time.localtime(value))

def ParseUSDate(mdy):
    return time.mktime(time.strptime(mdy, "%m/%d/%Y"))

def YYYYMMDDHHMMS(gmtSecondsSince1970 = None):
    value = _maybenow(gmtSecondsSince1970)
    return time.strftime("%Y%m%d%H%M%S", time.localtime(value))

def Duration(seconds):
    result = ':%02d' % (seconds % 60)
    seconds /= 60
    if seconds:
        result = '%02d%s' % (seconds % 60, result)
    seconds /= 60
    if seconds:
        result = '%02d:%s' % (seconds % 24, result)
    seconds /= 24
    if seconds:
        result = '%d days %s' % (seconds, result)
    return result

        
