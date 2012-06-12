#############################################################################
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#############################################################################

from Products.ZenUtils.FileCache import FileCache
import os

class DeviceConfigCache(object):
    def __init__(self, basepath):
        self.basepath = basepath

    def _getFileCache(self, monitor):
        return FileCache(os.path.join(self.basepath, monitor))

    def cacheConfigProxies(self, prefs, configs):
        for cfg in configs:
            self.updateConfigProxy(prefs, cfg)

    def updateConfigProxy(self, prefs, config):
        cache = self._getFileCache(prefs.options.monitor)
        key = config.configId
        cache[key] = config

    def deleteConfigProxy(self, prefs, deviceid):
        cache = self._getFileCache(prefs.options.monitor)
        key = deviceid
        try:
            del cache[key]
        except KeyError:
            pass

    def getConfigProxies(self, prefs, cfgids):
        cache = self._getFileCache(prefs.options.monitor)
        if cfgids:
            ret = []
            for cfgid in cfgids:
                if cfgid in cache:
                    config = cache[cfgid]
                    if config:
                        ret.append(config)
            return ret
        else:
            return filter(None, cache.values())
