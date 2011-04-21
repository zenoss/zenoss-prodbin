###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information plaease visit: http://www.zenoss.com/oss/
#
###########################################################################
import Migrate

import Globals

import logging
log = logging.getLogger("zen.migrate")

from Products.ZenModel.ZenossSecurity import *

class BanClassesOnAddToZenPackMenuItem(Migrate.Step):
    version = Migrate.Version(2, 1, 0)
    
    def cutover(self, dmd):  
        # Build menus
        dmd.buildMenus({
        'Organizer_list': [  {  'action': 'dialog_addToZenPack',
                                # All other orgs should not be packable
                               'allowed_classes': ('DeviceClass',),
                               'description': 'Add to ZenPack...',
                               'id': 'addToZenPack',
                               'isdialog': True,
                               'ordering': 0.0,
                               'permissions': (ZEN_MANAGE_DMD,) } ],
        'More': [ {  'action': 'dialog_addOneToZenPack',
                     'allowed_classes': ['ZenPackable'],
                     'banned_classes': ('DeviceGroup',
                                        'IpNetwork',
                                        'Location',
                                        'System',
                                        'RRDDataSource',
                                        'RRDDataPoint',
                                        'ThresholdClass',
                                        'GraphDefinition',
                                        'GraphPoint'
                                        ),
                     'description': 'Add to ZenPack...',
                     'id': 'addToZenPack',
                     'isdialog': True,
                     'ordering': 1.0,
                     'permissions': (ZEN_MANAGE_DMD,) } ]
        })
        
        zm = dmd.zenMenus
        if zm.User_list.zenMenuItems._getOb('addToZenPack', False):
            zm.User_list.zenMenuItems._delObject('addToZenPack') 
        if zm.Manufacturer_list.zenMenuItems._getOb('addToZenPack', False):
            zm.Manufacturer_list.zenMenuItems._delObject('addToZenPack')
        
        for menu in dmd.zenMenus():
            for item in menu.zenMenuItems():
                if item.id == 'addToZenPack':
                    item.permissions = (ZEN_MANAGE_DMD,)

BanClassesOnAddToZenPackMenuItem()
