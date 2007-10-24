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

import Globals

import logging
log = logging.getLogger("zen.migrate")

from Products.ZenModel.ZenossSecurity import *

class RemoveReportClassPageMenu(Migrate.Step):
    version = Migrate.Version(2, 2, 0)
    
    def cutover(self, dmd):
        # Build menus
        dmd.buildMenus({
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
                                        'GraphPoint',
                                        'ReportClass',
                                        ),
                     'description': 'Add to ZenPack...',
                     'id': 'addToZenPack',
                     'isdialog': True,
                     'ordering': 1.0,
                     'permissions': (ZEN_MANAGE_DMD,) } ]
        })  
        
        am = dmd.zenMenus._getOb('Add', None)
        if am:
            if am.zenMenuItems._getOb('addDeviceReport', False):
                am.zenMenuItems._delObject('addDeviceReport')
            if am.zenMenuItems._getOb('addReportClass', False):
                am.zenMenuItems._delObject('addReportClass')


RemoveReportClassPageMenu()
