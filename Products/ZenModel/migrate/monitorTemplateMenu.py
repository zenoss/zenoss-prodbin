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

class MonitorTemplateMenu(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
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
        for c in dmd.Monitors.objectValues(spec='MonitorClass'):
            c.buildRelations()
        for c in dmd.Monitors.objectValues(spec='Monitor'):
            c.buildRelations()
        dmd.Monitors.buildRelations()
        if len(dmd.Monitors.rrdTemplates()) == 0:
            from Products.ZenRelations.ImportRM import ImportRM
            from Products.ZenUtils.Utils import zenPath
            template = zenPath('Products/ZenModel/migrate/monitorTemplate.xml')
            im = ImportRM(noopts=True, app=dmd.zport)
            im.loadObjectFromXML(xmlfile=template)
        
monitorTemplateMenu = MonitorTemplateMenu()
