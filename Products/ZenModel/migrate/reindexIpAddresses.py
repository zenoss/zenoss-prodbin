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

import logging
log = logging.getLogger("zen.migrate")

class ReindexIpAddresses(Migrate.Step):
    version = Migrate.Version(3, 1, 70)

    def cutover(self, dmd):
        for x in zport.global_catalog():
            zport = dmd.getPhysicalRoot().zport
            zport.global_catalog.catalog_object(x.getObject(),
                                                idxs=['ipAddress'],
                                                update_metadata=True)

ReindexIpAddresses()
