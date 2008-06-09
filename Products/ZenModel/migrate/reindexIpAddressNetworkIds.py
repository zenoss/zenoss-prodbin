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

import Globals
import Migrate

class ReindexIpAddressNetworkIds(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):
        for brain in dmd.ZenLinkManager.layer3_catalog():
            try:
                ob = brain.getObject()
                ob.index_object()
            except:
                pass

ReindexIpAddressNetworkIds()
