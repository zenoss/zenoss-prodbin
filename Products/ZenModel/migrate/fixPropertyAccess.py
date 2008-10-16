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

import Migrate

from Products.ZenModel.ZenossSecurity import \
     MANAGER_ROLE, ZEN_MANAGER_ROLE, ZEN_USER_ROLE, OWNER_ROLE

class fixPropertyAccess(Migrate.Step):
    version = Migrate.Version(2, 2, 5)
    
    def cutover(self, dmd):
        dmd.manage_permission('Access contents information',
                              ['Authenticated',
                               MANAGER_ROLE,
                               ZEN_MANAGER_ROLE,
                               ZEN_USER_ROLE,
                               OWNER_ROLE],
                              0)
fixPropertyAccess()
