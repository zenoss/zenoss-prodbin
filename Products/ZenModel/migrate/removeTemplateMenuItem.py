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

def addMenuItems( dmd, menuId, menuItems ):
    dsMenu = dmd.zenMenus._getOb( menuId, None)        
    for menuItem in menuItems:
        if dsMenu and not dsMenu.zenMenuItems._getOb( menuItem['id'], None):
            dsMenu.manage_addZenMenuItem( **menuItem )


class removeTemplateMenuItem(Migrate.Step):
    version = Migrate.Version(3, 0, 0)
    
    def cutover(self, dmd):
        
        items = dmd.zenMenus._getOb('PerformanceMonitor_list').zenMenuItems
        if hasattr(items, 'performanceTemplates'):        
            items._delObject('performanceTemplates')
        addMenuItems( dmd, 'PerformanceMonitor_list', [
                {  'action': 'rrdTemplates/PerformanceConf/viewRRDTemplate',
                    'description': 'Performance Template',
                    'id': 'performanceConf',
                    'isdialog': False,
                    'isglobal': True,
                    'ordering': 16.0,
                    'permissions': ('View Device',) } ] )


removeTemplateMenuItem()
