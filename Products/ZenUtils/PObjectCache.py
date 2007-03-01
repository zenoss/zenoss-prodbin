#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

"""PObjectCache

Persistent object cache that should be placed in a temp_folder

$Id: PObjectCache.py,v 1.2 2003/04/11 15:50:18 edahl Exp $"""

__version__ = "$Revision: 1.2 $"[11:-2]

import time

from Globals import Persistent
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo

from OFS.SimpleItem import SimpleItem

class PObjectCache(SimpleItem):
    editCache = DTMLFile('dtml/editCache', globals())
    manage_options = ({'label':'Cache','action':'editCache'},)

    security = ClassSecurityInfo()

    def __init__(self, id, timeout=20, clearthresh=20):
        self.id = id
        self.timeout = timeout
        self.clearthresh = clearthresh
        self.cache = {}

    
    def checkCache(self, key):
        """check to see if key is in cache return None if not"""
        if self.cache.has_key(key):
            cobj = self.cache[key]
            if cobj.checkTime(): 
                return cobj.getObj()
            else:
                del self.cache[key]
                self._p_changed = 1
        return None


    def addToCache(self, key, obj):
        """add an object to the cache"""
        cobj = CacheObj(obj, self.timeout)
        self.cache[key] = cobj

    def manage_clearCache(self, REQUEST=None):
        self.cleanCache(force=1)
        if REQUEST:
            return self.editCache(self, REQUEST, "cleared cache") 

        
    def cleanCache(self, force=0):
        """clean the cache if nessesary"""
        cleared = 0
        if self.cache:
            self.clearcount -= 1
            if force or self.clearcount < self.clearthresh:
                for key, value in self.cache.items():
                    if not value.checkTime():
                        cleared = 1
                        del self.cache[key]
                self.clearcount = self.clearthresh
        return cleared


    def getCache(self):
        return self.cache


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
