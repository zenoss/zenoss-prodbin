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

import threading
import time

class Timed:
    "Store elements in a map for the given time"

    def __init__(self, map, timeout):
        self.map = map
        self.timeout = timeout
        self.lastClean = 0


    def clean(self, now = None):
        "remove old values"
        # FIXME O(N) search
        if now is None:
            now = time.time()
        if self.lastClean + self.timeout > now:
            return
        for k, (v, t) in self.map.items():
            if t + self.timeout < now:
                del self.map[k]
        self.lastClean = now

    
    def get(self, key, default):
        now = time.time()
        self.clean(now)
        v, t = self.map.get(key, (default, None) )
        if t is None or t + self.timeout < now:
            return default
        return v


    def __getitem__(self, key):
        now = time.time()
        v, t = self.map[key]
        if t + self.timeout < now:
            del self.map[key]
            raise KeyError
        return v


    def __setitem__(self, key, value):
        now = time.time()
        self.clean(now)
        self.map[key] = (value, now)


    def update(self, d):
        now = time.time()
        self.clean(now)
        for k, v in d.items():
            self.map[k] = (v, now)


class Locked:
    "Use a simple lock for all read/write access to a map"

    def __init__(self, map):
        self.map = map
        self.lock = threading.Lock()


    def impl(self, m, *args, **kw):
        "call a method on the map, with the lock held"
        self.lock.acquire()
        try:
            return m(*args, **kw)
        finally:
            self.lock.release()

        
    def has_key(self, *args, **kw):
        return self.impl(self.map.has_key, *args, **kw)


    def get(self, *args, **kw):
        return self.impl(self.map.get, *args, **kw)

        
    def __setitem__(self, *args, **kw):
        return self.impl(self.map.__setitem__, *args, **kw)


    def __getitem__(self, *args, **kw):
        return self.impl(self.map.__getitem__, *args, **kw)


    def update(self, *args, **kw):
        return self.impl(self.map.update, *args, **kw)

