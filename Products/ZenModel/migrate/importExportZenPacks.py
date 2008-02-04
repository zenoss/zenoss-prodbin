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


class ImportExportZenPacks(Migrate.Step):
    version = Migrate.Version(2, 2, 0)
    
    def cutover(self, dmd):
        zenPackListMenu = dmd.zenMenus.ZenPack_list
        if zenPackListMenu.zenMenuItems._getOb('installZenPack',None):
            zenPackListMenu.zenMenuItems._delObject('installZenPack')
        zenPackListMenu.manage_addZenMenuItem(
                id='installZenPack',
                description='Install ZenPack...',
                action='dialog_installZenPack',
                isdialog=True,
                permissions=('Manage DMD',),
                ordering=1.00)

ImportExportZenPacks()
