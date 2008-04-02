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

from Products.ZenModel.LinkManager import manage_addLinkManager

import logging
log = logging.getLogger("zen.migrate")

class NetworkIndexes(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):  
        try:
            getattr(dmd.ZenLinkManager, 'layer3_catalog')
        except AttributeError:
            try:
                dmd.manage_delObjects('ZenLinkManager')
            except AttributeError:
                pass
            manage_addLinkManager(dmd)


networkindexes = NetworkIndexes()
