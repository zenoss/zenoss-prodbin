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

import Migrate

def addMenuItems( dmd, menuId, menuItems ):
    dsMenu = dmd.zenMenus._getOb( menuId, None)        
    for menuItem in menuItems:
        if dsMenu and not dsMenu.zenMenuItems._getOb( menuItem['id'], None):
            dsMenu.manage_addZenMenuItem( **menuItem )

class addDataPointAliasMenus(Migrate.Step):
    version = Migrate.Version(2, 4, 0)

    def cutover(self, dmd):
        dmd.buildMenus({  
            'DataPointProperties_list': [
                     {  'action': 'dialog_removeDataPointAlias',
                        'isdialog': True,
                        'description': 'Remove Data Point Alias...',
                        'id': 'removeDataPointAlias',
                        'ordering': 90,
                        'permissions': ('Change Device',)},
                     {  'action': 'dialog_addDataPointAlias',
                        'isdialog': True,
                        'description': 'Add Data Point Alias...',
                        'id': 'addDataPointAlias',
                        'ordering': 100,
                        'permissions': ('Change Device',)},
                     ]} )
        
        addMenuItems( dmd, 'SimpleDataPoint_list', [
                     {  'action': 'dialog_removeDataPointAlias',
                        'isdialog': True,
                        'description': 'Remove Data Point Alias...',
                        'id': 'removeDataPointAlias',
                        'ordering': 90,
                        'permissions': ('Change Device',)},
                     {  'action': 'dialog_addDataPointAlias',
                        'isdialog': True,
                        'description': 'Add Data Point Alias...',
                        'id': 'addDataPointAlias',
                        'ordering': 100,
                        'permissions': ('Change Device',)},
                     ] )
        

        
addDataPointAliasMenus()