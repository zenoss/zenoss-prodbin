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

from Products.ZenHub.HubService import HubService
from Products.ZenHub.PBDaemon import translateError


class TrapService(HubService):

    @translateError
    def remote_getOidMap(self):
        """
        Return a dictionary containing all OID -> Name mappings from /Mibs.
        """
        oidMap = {}
        for brain in [ b for b in self.dmd.Mibs.mibSearch() if b.oid ]:
            oidMap[brain.oid] = brain.id

        return oidMap
