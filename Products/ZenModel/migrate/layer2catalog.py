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

class Layer2Catalog(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):  

        # Add the catalog
        try:
            getattr(dmd.ZenLinkManager, 'layer2_catalog')
        except AttributeError:
            _create_layer2_catalog(dmd.ZenLinkManager)

        # Reindex the interfaces
        for device in dmd.Devices.getSubDevicesGen():
            for iface in device.getSubComponents("IpInterface"):
                iface.index_object()

Layer2Catalog()
