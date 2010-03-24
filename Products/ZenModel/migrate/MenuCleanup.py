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

class MenuCleanup(Migrate.Step):
    version = Migrate.Version(2, 6, 0)
    
    def cutover(self, dmd):
        
        zenMenus = dmd.zenMenus
        
        edit = zenMenus.Edit
        removeItems(edit, ['setGroups', 'setLocation', 'setPerformanceMonitor',
                           'setPriority', 'setProductionState', 'setSystems'])

        topLevel = zenMenus.TopLevel
        removeItems(topLevel, ['clearMapCache'])
        
        manage = zenMenus.Manage
        removeItems(manage, ['addDevice', 'lockDevices', 'pushConfig', 
                             'resetCommunity', 'resetIp'])
        
def removeItems(menu, items):
    for item in items:
        if hasattr(menu.zenMenuItems, item):
            menu.zenMenuItems._delObject(item)
MenuCleanup()
