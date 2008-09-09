###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information plaease visit: http://www.zenoss.com/oss/
#
###########################################################################
import Migrate

import Globals

from Products.ZenModel.LinkManager import _create_layer2_catalog

import logging
log = logging.getLogger("zen.migrate")

import sys


class Layer2Catalog(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):  

        # Add the catalog
        try:
            getattr(dmd.ZenLinkManager, 'layer2_catalog')
        except AttributeError:
            _create_layer2_catalog(dmd.ZenLinkManager)

        # Reindex the interfaces
        print "Indexing interfaces. This may take a while."

        def _update(i):
            if   i % 5000 == 0 and i > 0: print i,
            elif i % 1000 == 0: print '.',
            sys.stdout.flush()

        for i, iface in enumerate(dmd.Devices.getSubComponents("IpInterface")):
            iface.index_object()
            _update(i)


Layer2Catalog()
