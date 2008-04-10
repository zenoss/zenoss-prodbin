###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information plaease visit: http://www.zenoss.com/oss/
#
###########################################################################
import Migrate

from Products.ZenModel.ZenossSecurity import *

class MoveHistoryToMoreMenu(Migrate.Step):
    version = Migrate.Version(2, 2, 0)
    
    def cutover(self, dmd):
        # Build menus
        dmd.buildMenus({
        'More': [ {  'action': 'viewHistoryEvents',
                     'allowed_classes': ['EventClass', 'EventClassInst', 
                        'Device', 'DeviceOrganizer', 'Location', 'System',
                        'DeviceClass'],
                     'banned_classes' : ['IpNetwork'],
                     'description': 'Event History',
                     'id': 'historyEvents',
                     'ordering': 1.0,
                     'permissions': (ZEN_VIEW,) } ]
        })
        viewHistory = dmd.zenMenus.More.zenMenuItems.viewHistory
        if not viewHistory.banned_classes:
            viewHistory.banned_classes = ('IpNetwork',)


MoveHistoryToMoreMenu()
