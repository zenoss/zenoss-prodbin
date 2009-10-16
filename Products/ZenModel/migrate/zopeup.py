###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import warnings
import os.path

from Products.CMFCore.DirectoryView import DirectoryInformation

import Migrate

class ZopeUpgrade(Migrate.Step):
    version = Migrate.Version(2, 5, 0)

    def cutover(self, dmd):
        if getattr(dmd.zport, '_components', None) is None:
            dmd.zport._components = None

        # Registration key of DirectoryViews changed format, for some reason;
        # now needs to have package prepended. Fine for stuff in Products, but
        # ZenPacks need to have it done manually.

        # Temporarily suppress UserWarnings; they're expected here
        _origfilters = warnings.filters[:]
        warnings.simplefilter('ignore', UserWarning)

        for pack in dmd.ZenPackManager.packs():
            skinsdir = pack.path('skins')
            if not os.path.isdir(skinsdir):
                continue
            info = DirectoryInformation(skinsdir, skinsdir)
            for subdir in info.getSubdirs():
                try:
                    dview = dmd.portal_skins[subdir]
                except KeyError:
                    # DirectoryView isn't there, nothing we can do
                    pass
                else:
                    path = dview._dirpath
                    prefix = pack.__name__ + ':'
                    if not path.startswith(prefix):
                        dview._dirpath = prefix + path

        # Reset warning filters back to their original state
        warnings.filters = _origfilters


ZopeUpgrade()
