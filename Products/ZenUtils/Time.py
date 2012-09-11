##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""Time

Utilities for consistent manipulation of Dates and Time.  All simple
code should migrate here, and without dependencies on anything other
than standard python libraries.

$Id:$"""

__version__ = "$$"[11:-2]

import time
from math import isnan

def _maybenow(gmtSecondsSince1970):
    if gmtSecondsSince1970 is None:
        return time.time()
    return int(gmtSecondsSince1970)

def LocalDateTime(gmtSecondsSince1970 = None):
    value = _maybenow(gmtSecondsSince1970)
    secs = value % 60
    return time.strftime("%Y/%m/%d %H:%M:%%06.3f", time.localtime(value)) % secs

def LocalDateTimeFromMilli(milliseconds):
    """
    @param milliseconds:: UTC timestamp in milliseconds
    """
    return LocalDateTime(milliseconds / 1000)


def isoDateTime(gmtSecondsSince1970 = None):
    value = _maybenow(gmtSecondsSince1970)
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(value))

def isoDateTimeFromMilli(milliseconds):
    """
    @param milliseconds:: UTC timestamp in milliseconds
    """
    return isoDateTime(milliseconds / 1000)

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
    if isnan(seconds):
        return "nan"

    seconds = int(seconds)
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


def getBeginningOfDay(gmtSecondsSince1970=None):
    value = _maybenow(gmtSecondsSince1970)
    return time.mktime(time.localtime(value)[:3] + (0,0,0,0,0,-1))


def getEndOfDay(gmtSecondsSince1970=None):
    value = _maybenow(gmtSecondsSince1970)
    return time.mktime(time.localtime(value)[:3] + (23,59,59,0,0,-1))

def isoToTimestamp(value):
    """
    converts a iso time string that does not contain a timezone, ie.
    YYYY-MM-DD HH:MM:SS, to a timestamp in seconds since 1970; uses the system
    timezone
    """
    timeStr = value.replace('T', ' ')
    timeTuple = time.strptime(timeStr, '%Y-%m-%d %H:%M:%S')
    timestamp = time.mktime(timeTuple)
    return timestamp
