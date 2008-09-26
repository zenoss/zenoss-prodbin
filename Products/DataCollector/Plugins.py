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

__doc__= """Load plugins from standard locations and from ZenPacks
"""

from Products.ZenUtils.Utils import importClass, zenPath
import sys
import os

import logging
log = logging.getLogger('zen.plugins')

_pluginskip = ("CollectorPlugin.py", "DataMaps.py")
def _plfilter(f):
    """Return a filtered list of plugins
    """
    return (f.endswith(".py")   and
            not f.startswith('.') and
            f.find('#') < 0       and 
            not f.startswith("_") and
            not f in _pluginskip)


from twisted.spread import pb
class PluginLoader(pb.Copyable, pb.RemoteCopy):
    """Class to load plugins
    """

    def __init__(self, package, modpath):
        """Initializer
        """
        self.package = package
        self.modpath = modpath
    
    def pluginName(self):
        """Return the name of the plugin
        """
        return self.modpath.split('plugins.').pop()
        
    def create(self):
        """Load and compile the code contained in the given plugin
        """

        moduleName = self.modpath.split('.')[0]
        sys.path.insert(0, self.package)
        const = importClass(self.modpath)
        sys.path.remove(self.package)

        del sys.modules[moduleName]

        plugin = const()
        return plugin

pb.setUnjellyableForClass(PluginLoader, PluginLoader)


def _loadPluginDir(pdir):
    """Load the Zenoss default collector plugins
    """
    collectorPlugins = []
    log.info("Loading collector plugins from: %s", pdir)
    lpdir = len(pdir)+1
    for path, dirname, filenames in os.walk(pdir):
        path = path[lpdir:]
        for filename in filter(_plfilter, filenames):
            modpath = os.path.join(path,filename[:-3]).replace("/",".")
            log.debug("Loading: %s", modpath)
            try:
                collectorPlugins.append( PluginLoader(pdir, modpath) )
            except ImportError:
                log.exception("Problem loading plugin:%s" % modpath)
    return collectorPlugins
 


def loadPlugins(dmd):
    """Load plugins from the Zenoss plugin directory and from the plugin
    directory from each ZenPack.  Returns them as a list of PluginLoader instances.
    """
    plugins = [x for x in sys.modules if x.startswith("plugins")]
    PDIR = os.path.join(os.path.dirname(__file__), "plugins")
    for key in ['zenoss'] + plugins:
        log.debug("Clearing plugin %s", key)
        if sys.modules.has_key(key):
            del sys.modules[key]

    plugins = _loadPluginDir(PDIR)
    plugins += _loadPluginDir(zenPath('Products/ZenWin/modeler/plugins'))

    try:
        for pack in dmd.ZenPackManager.packs():
            if pack.isEggPack():
                 eggPlugins = _loadPluginDir(pack.path('modeler', 'plugins'))
                 for eggPlugin in eggPlugins:
                    eggPlugin.modpath = '%s.modeler.plugins.%s' % \
                        (pack.moduleName(), eggPlugin.modpath)
                 plugins += eggPlugins
            else:
                plugins += _loadPluginDir(pack.path('modeler', 'plugins'))

    except:
        log.error('Could not load modeler plugins from ZenPacks.'
                  ' One of the ZenPacks is missing or broken.')
    return plugins


