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

from Products.ZenUtils.Utils import importClass, zenPath
import sys
import os

import logging
log = logging.getLogger('zen.plugins')

_pluginskip = ("CollectorPlugin.py", "DataMaps.py")
def _plfilter(f):
    return (f.endswith(".py")   and
            not f.startswith('.') and
            f.find('#') < 0       and 
            not f.startswith("_") and
            not f in _pluginskip)

from twisted.spread import pb
class PluginLoader(pb.Copyable, pb.RemoteCopy):
    def __init__(self, package, modpath):
        self.package = package
        self.modpath = modpath
        
    def create(self):
        sys.path.insert(0, self.package)
        const = importClass(self.modpath)
        sys.path.remove(self.package)
        moduleName = self.modpath.split('.')[0]
        del sys.modules[moduleName]
        plugin = const()
        return plugin

pb.setUnjellyableForClass(PluginLoader, PluginLoader)


def _loadPluginDir(pdir):
    collectorPlugins = []
    log.info("loading collector plugins from: %s", pdir)
    lpdir = len(pdir)+1
    for path, dirname, filenames in os.walk(pdir):
        path = path[lpdir:]
        for filename in filter(_plfilter, filenames):
            modpath = os.path.join(path,filename[:-3]).replace("/",".")
            log.debug("loading: %s", modpath)
            try:
                collectorPlugins.append(PluginLoader(pdir, modpath))
            except ImportError:
                log.exception("problem loading plugin:%s",modpath)
    return collectorPlugins
 

def loadPlugins(dmd):
    """Load plugins from the plugin directory.  Returns them as a list of
    PluginLoader instances."""
    plugins = [x for x in sys.modules if x.startswith("plugins")]
    PDIR = os.path.join(os.path.dirname(__file__), "plugins")
    for key in ['zenoss'] + plugins:
        log.debug("clearing plugin %s", key)
        if sys.modules.has_key(key):
            del sys.modules[key]
    plugins = _loadPluginDir(PDIR)
    plugins += _loadPluginDir(zenPath('Products/ZenWin/modeler/plugins'))
    try:
        for pack in dmd.packs():
            if pack.isEggPack():
                 eggPlugins = _loadPluginDir(pack.path('modeler', 'plugins'))
                 for eggPlugin in eggPlugins:
                    eggPlugin.modpath = '%s.modeler.plugins.%s' % \
                        (pack.moduleName(), eggPlugin.modpath)
                 plugins += eggPlugins
            else:
                plugins += _loadPluginDir(pack.path('modeler', 'plugins'))
    except:
        log.error('Could not load modeler plugins from zenpacks.'
                  ' One of the zenpacks is missing or broken.')
    return plugins


