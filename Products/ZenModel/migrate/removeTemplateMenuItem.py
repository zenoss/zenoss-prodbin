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

class RemoveTemplateMenuItem(Migrate.Step):
    version = Migrate.Version(2, 5, 70)
    
    def cutover(self, dmd):
        
        items = dmd.zenMenus._getOb('PerformanceMonitor_list').zenMenuItems
        if hasattr(items, 'performanceTemplates'):        
            items._delObject('performanceTemplates')


RemoveTemplateMenuItem()
