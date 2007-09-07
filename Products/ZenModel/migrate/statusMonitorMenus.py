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

class StatusMonitorMenus(Migrate.Step):
    version = Migrate.Version(2, 1, 0)
    
    def cutover(self, dmd):
        
        # Build menus
        dmd.buildMenus({  
            'Device_list': [
                {  'action': 'dialog_setStatusMonitors',
                   'description': 'Set Status Monitors...',
                   'id': 'setStatusMonitors',
                   'isdialog': True,
                   'ordering': 16.0,
                   'permissions': ('Change Device',),
                }],
            'DeviceGrid_list': [
                {  'action': 'dialog_setStatusMonitors_grid',
                   'description': 'Set Status Monitors...',
                   'id': 'setStatusMonitors_grid',
                   'isdialog': True,
                   'ordering': 15.0,
                   'permissions': ('Change Device',),
                }],
            'Edit': [  
                {  'action':'dialog_setStatusMonitors_global',
                   'description': 'Set Status Monitors...',
                   'id': 'setStatusMonitors',
                   'allowed_classes': ( 'DeviceClass',
                                         'DeviceGroup',
                                         'Location',
                                         'System'),
                   'isdialog': True,
                   'ordering': 15.0,
                   'permissions': ('Change Device',)
                }],
        })


StatusMonitorMenus()
