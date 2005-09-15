#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

"""NcoProduct

Data connector for Micromuse Omnibus

$Id: ObjectCache.py,v 1.7 2003/04/14 21:08:25 edahl Exp $"""

__version__ = "$Revision: 1.7 $"[11:-2]

from Globals import Persistent
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
import time

class ObjectCache(Persistent):
    editCache = DTMLFile('dtml/editCache', globals())
    manage_options = ({'label':'Cache','action':'editCache'},)

    security = ClassSecurityInfo()

    def __init__(self, timeout=20, clearthresh=20):
        self.timeout = timeout
        self.clearthresh = clearthresh

    def initCache(self):
        """make sure that volitile attributes exist"""
        if not hasattr(self, '_v_cache'):
            self._v_cache = {}
        if not hasattr(self, '_v_clearcount'):
            self._v_clearcount = self.clearthresh

    def checkCache(self, key):
        """check to see if key is in cache return None if not"""
        self.initCache()
        if self._v_cache.has_key(key):
            cobj = self._v_cache[key]
            if cobj.checkTime(): 
                return cobj.getObj()
            else:
                del self._v_cache[key]
        return None


    def addToCache(self, key, obj):
        """add an object to the cache"""
        self.initCache()
        cobj = CacheObj(obj, self.timeout)
        self._v_cache[key] = cobj


    def cleanCache(self, force=0):
        """clean the cache if nessesary"""
        self.initCache()
        cleared = 0
        if self._v_cache:
            self._v_clearcount -= 1
            if force or self._v_clearcount < self.clearthresh:
                for key, value in self._v_cache.items():
                    if not value.checkTime():
                        cleared = 1
                        del self._v_cache[key]
                self._v_clearcount = self.clearthresh
        return cleared
        
    def getCache(self):
        self.initCache()
        return self._v_cache

    security.declareProtected('View','getCacheTimeout')
    def getCacheTimeout(self):
        """return cache timeout"""
        return self.timeout

    security.declareProtected('View','getCacheClearthresh')
    def getCacheClearthresh(self):
        """return cache clearthresh"""
        return self.clearthresh

class CacheObj:
    
    def __init__(self, obj, timeout):
        self._obj = obj
        self._timeout = timeout
        self._time = time.time()

    def checkTime(self):
        if self._time + self._timeout < time.time():
            return 0
        else:
            return 1  
    
    def getObj(self):
        return self._obj

    def getTime(self):
        """Return the time at which this cache object was created"""
        return self._time
