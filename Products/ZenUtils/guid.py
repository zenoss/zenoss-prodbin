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
"""
Generate a globally unique id that is used for events.  The id has 4 parts:
 * mac address (or random number) - 6 hex characters
 * the process id - 4 hex characters
 * time - 8 hex characters - refreshed when counter wraps
 * decrementing number - 7 hex characters
"""
import math, sys, time, random, threading, os, re

def _getmac():
    """
    try to get one of the mac addresses from our interfaces.  if we fail get a
    random number.  we limit the return value to 8 characters because we used
    to use ip addresses that were this long.  the length is important because
    it determins the length of the final guid.
    """
    output = ""
    if os.path.exists('/sbin/ifconfig'):
        output = os.popen('/sbin/ifconfig -a').read()
    elif os.path.exists('/usr/sbin/ifconfig'):
        output = os.popen('/usr/sbin/ifconfig -a').read()
    m = re.search("([0-9a-fA-F]{1,2}:){5}[0-9a-fA-F]{1,2}",output)
    if m:
        mac = m.group(0)
        mac = mac.replace(':', '')
    else:
        mac = "%06x" % random.Random().randrange(0,0xffffff)
    return mac[-6:]

_mac = _getmac()
_pid = '%04x' % os.getpid()
_base = _mac + _pid

def _getstarttime():
    return "%08x" % time.time()
_starttime = _getstarttime()

def _unique_sequencer():
    _XUnit_sequence = 0xfffffff
    while 1:
        yield _XUnit_sequence
        _XUnit_sequence -= 1
        if _XUnit_sequence <= 0:
            global _starttime 
            _starttime = _getstarttime()
            _XUnit_sequence = 0xfffffff
_uniqueid = _unique_sequencer()

lock = threading.RLock()
def generate():
    lock.acquire()
    try:
        return  "%s%s%07x" % (_base, _starttime, _uniqueid.next())
    finally:
        lock.release()
