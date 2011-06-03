###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import Migrate

class RemoveEventMenus(Migrate.Step):
    version = Migrate.Version(3, 1, 70)

    def cutover(self, dmd):
        zenMenus = dmd.zenMenus

        # Remove menu items
        topLevel = zenMenus.TopLevel
        removeItems(topLevel, 'addEvent', 'manage_clearCache', 'manage_clearHeartbeats', 'manage_refreshConversions')

        # Remove menus
        removeMenus(dmd.zenMenus, 'ActionRuleWindow_list', 'ActionRule_list', 'EventView_list', 'Event_list',
                    'HistoryEvent_list')


def removeItems(menu, *items):
    for item in items:
        if hasattr(menu.zenMenuItems, item):
            menu.zenMenuItems._delObject(item)

def removeMenus(zenMenus, *menus):
    for menu in menus:
        if hasattr(zenMenus, menu):
            zenMenus._delObject(menu)

RemoveEventMenus()
