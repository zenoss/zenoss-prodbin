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

class RestoreRemoveZenPackMenuItem(Migrate.Step):
    version = Migrate.Version(2, 2, 0)
    
    def cutover(self, dmd):
        
        zpMenu = getattr(dmd.zenMenus, 'ZenPack_list', None)
        if zpMenu:
            # Remove existing
            if zpMenu.zenMenuItems._getOb('removeZenPack', None):
                zpMenu.zenMenuItems._delObject('removeZenPack')

            # Recreate
            zpMenu.manage_addZenMenuItem(
                id='removeZenPack',
                description='Delete ZenPack...',
                action='dialog_removeZenPacks',
                isdialog=True,
                permissions=('Manage DMD',),
                ordering=1.0
                )

RestoreRemoveZenPackMenuItem()
