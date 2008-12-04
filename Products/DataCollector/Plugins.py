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

__doc__= """Plugins
Load plugins from standard locations and from ZenPacks
"""

from Products.ZenUtils.Utils import importClass, zenPath
import sys
import os
import exceptions

import logging
log = logging.getLogger('zen.plugins')

_pluginskip = ("CollectorPlugin.py", "DataMaps.py")
def _plfilter(f):
    """
    Return a filtered list of plugins

    @param f: plugin name
    @type f: string
    """
    return (f.endswith(".py")   and
            not f.startswith('.') and
            f.find('#') < 0       and
            not f.startswith("_") and
            not f in _pluginskip)


class pluginImportError(exceptions.ImportError):
    """
    Capture extra data from plugin exceptions
    """

    def __init__(self, plugin='', traceback='' ):
        """
        Initializer

        @param plugin: plugin name
        @type plugin: string
        @param traceback: traceback from an exception
        @type traceback: traceback object
        """
        self.plugin = plugin
        self.traceback = traceback
        # The following is needed for zendisc
        self.args = traceback



from twisted.spread import pb
class PluginLoader(pb.Copyable, pb.RemoteCopy):
    """
    Class to load plugins
    """

    def __init__(self, package, modpath):
        """
        Initializer

        @param package: package path where the plugins may be located
        @type package: string
        @param modpath: plugin path inside of the package
        @type modpath: string
        """
        self.package = package
        self.modpath = modpath


    def pluginName(self):
        """
        Return the name of the plugin

        @return: name of the plugin
        @rtype: string
        """
        return self.modpath.split('plugins.').pop()


    def create(self):
        """
        Load and compile the code contained in the given plugin
        """

        moduleName = self.modpath.split('.')[0]
        try:
            sys.path.insert(0, self.package)
            const = importClass(self.modpath)
            sys.path.remove(self.package)

        except (SystemExit, KeyboardInterrupt):
            raise

        except:
            import traceback
            raise pluginImportError( plugin=self.modpath, \
                                    traceback=traceback.format_exc() )

        del sys.modules[moduleName]

        plugin = const()
        return plugin

pb.setUnjellyableForClass(PluginLoader, PluginLoader)



def _loadPluginDir(pdir):
    """
    Load the Zenoss default collector plugins

    @param pdir: plugin path parent directory
    @type pdir: string
    @return: list of loadable plugins
    @rtype: list
    """
    collectorPlugins = []
    log.debug("Loading collector plugins from: %s", pdir)
    lpdir = len(pdir)+1
    for path, dirname, filenames in os.walk(pdir):
        path = path[lpdir:]
        for filename in filter(_plfilter, filenames):
            modpath = os.path.join(path,filename[:-3]).replace("/",".")
            log.debug("Loading: %s", modpath)
            try:
                this_plugin= PluginLoader(pdir, modpath)
                if this_plugin is not None:
                    collectorPlugins.append( this_plugin )
            except ImportError:
                log.exception("Problem loading plugin:%s" % modpath)

    return collectorPlugins



def loadPlugins(dmd):
    """
    Load plugins from the Zenoss plugin directory and from the plugin
    directory from each ZenPack.
    Returns them as a list of PluginLoader instances.

    @param dmd: Device Management Database (DMD) reference
    @type dmd: dmd object
    @return: list of loadable plugins
    @rtype: list
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
            try:
                if pack.isEggPack():
                     eggPlugins = _loadPluginDir(pack.path('modeler', 'plugins'))
                     for eggPlugin in eggPlugins:
                        eggPlugin.modpath = '%s.modeler.plugins.%s' % \
                            (pack.moduleName(), eggPlugin.modpath)
                     plugins += eggPlugins
                else:
                    plugins += _loadPluginDir(pack.path('modeler', 'plugins'))
            except:
                log.error('Could not load modeler plugins from the %s ZenPack.' \
                          % pack.name )

    except:
        log.error('Could not load modeler plugins from ZenPacks.'
                  ' One of the ZenPacks is missing or broken.')
    return plugins
