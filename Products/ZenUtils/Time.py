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

def HHMMSS(gmtSecondsSince1970 = None):
    value = _maybenow(gmtSecondsSince1970)
    return time.strftime("%H:%M:%S", time.localtime(value))

def SaveMessage():
    return "Saved at time: " + HHMMSS()

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

        
