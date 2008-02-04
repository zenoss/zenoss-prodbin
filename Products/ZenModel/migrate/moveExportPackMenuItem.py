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


class MoveExportPackMenuItem(Migrate.Step):
    version = Migrate.Version(2, 2, 0)
    

    def cutover(self, dmd):

        # Remove "Export ZenPack" item from the ZenPack menu.
        zenPackMenu = dmd.zenMenus._getOb('ZenPack', None)
        if zenPackMenu and \
            zenPackMenu.zenMenuItems._getOb('exportZenPack', None):
            zenPackMenu.zenMenuItems._delObject('exportZenPack')

        # Add to the More menu
        moreMenu = dmd.zenMenus._getOb('More', None)
        if moreMenu:
            moreMenu.manage_addZenMenuItem(
                id='exportZenPack',
                description='Export ZenPack...',
                action='dialog_exportPack',
                permissions=('Manage DMD',),
                isdialog=True,
                isglobal=True,
                ordering=1.01,
                allowed_classes=('ZenPack',))


MoveExportPackMenuItem()
