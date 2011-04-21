###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################


import Migrate

class StatusMonitorMenus(Migrate.Step):
    version = Migrate.Version(2, 1, 0)
    
    def cutover(self, dmd):
        
        # Build menus
        dmd.buildMenus({  
            'PerformanceMonitor_list': [
                {  'action': 'performanceTemplates',
                   'description': 'Templates',
                   'id': 'performanceTemplates',
                   'ordering': 16.0,
                   'permissions': ('View Device',),
                }],
            'StatusMonitor_list': [
                {  'action': 'performanceTemplates',
                   'description': 'Templates',
                   'id': 'performanceTemplates',
                   'ordering': 16.0,
                   'permissions': ('View Device',),
                }],
        })


StatusMonitorMenus()
