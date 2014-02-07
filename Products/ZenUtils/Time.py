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
import os
import pytz
from datetime import datetime    
from hashlib import sha224
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


SERVER_TIMEZONE = None
def getServerTimeZone():
    """
    This is suprisingly harder than you would think, but we need to guess
    the olson timezone on the current server. Most Redhaty linuxes symlink
    /etc/localtime. For the rest we need to compare the hash of what is in
    /usr/share/zoneinfo
    """
    global SERVER_TIMEZONE
    if not SERVER_TIMEZONE is None:
        return SERVER_TIMEZONE
    # try reading the link
    if os.path.islink('/etc/localtime'):
        SERVER_TIMEZONE = '/'.join(os.readlink('/etc/localtime').split('/')[-2:])
        return SERVER_TIMEZONE
    tzfile_digest = None
    with open('/etc/localtime') as tzfile:    
        tzfile_digest = sha224(tzfile.read()).hexdigest()    
    
    for root, dirs, filenames in os.walk("/usr/share/zoneinfo/"):
        for filename in filenames:
            fullname = os.path.join(root, filename)
            f = open(fullname)
            digest = sha224(f.read()).hexdigest()
            if digest == tzfile_digest:
                SERVER_TIMEZONE = '/'.join((fullname.split('/'))[-2:])
                return SERVER_TIMEZONE
            f.close()
        # if we haven't found it don't keep trying next request
        SERVER_TIMEZONE = ""
        return SERVER_TIMEZONE

def convertTimestampToTimeZone(timestamp, zone_name, fmt="%Y/%m/%d %H:%M:%S"):
    """
    This takes a integer timestamp (in seconds since epoch) and returns a
    string that represents the time in the timezone name in the provided format.
    """    
    utc_tz = pytz.timezone('UTC')
    utc_dt = utc_tz.localize(datetime.utcfromtimestamp(timestamp))
    try:
        localized_tz = pytz.timezone(zone_name)
    except pytz.UnknownTimeZoneError:
        # return server time
        return isoDateTime(timestamp, fmt)     
    localized_dt = localized_tz.normalize(utc_dt.astimezone(localized_tz))
    return localized_dt.strftime(fmt)
    
def isoDateTime(gmtSecondsSince1970 = None, fmt="%Y-%m-%d %H:%M:%S"):
    value = _maybenow(gmtSecondsSince1970)
    return time.strftime(fmt, time.localtime(value))

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
