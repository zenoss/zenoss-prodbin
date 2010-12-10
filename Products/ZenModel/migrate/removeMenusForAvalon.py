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

class RemoveMenusForAvalon(Migrate.Step):
    version = Migrate.Version(3, 1, 0)

    def cutover(self, dmd):
        menus = dmd.zenMenus.TopLevel.zenMenuItems
        menus._delObject('manage_clearCache')
        menus._delObject('manage_refreshConversions')


RemoveMenusForAvalon()
