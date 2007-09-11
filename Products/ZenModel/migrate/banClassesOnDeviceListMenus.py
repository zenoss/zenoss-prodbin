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

from Products.ZenModel.ZenossSecurity import ZEN_CHANGE_DEVICE

class BanClassesOnDeviceListMenus(Migrate.Step):
    version = Migrate.Version(2, 1, 0)

    def cutover(self, dmd):  
        # Build menus
        dmd.buildMenus({
        'Device_list': [  
                    {  'action': 'dialog_setProductionState',
                       'banned_classes': ['Monitor'],
                       'description': 'Set Production State...',
                       'id': 'setProductionState',
                       'isdialog': True,
                       'ordering': 80.0,
                       'permissions': (ZEN_CHANGE_DEVICE,)},
                    {  'action': 'dialog_setPriority',
                       'banned_classes': ['Monitor'],
                       'description': 'Set Priority...',
                       'id': 'setPriority',
                       'isdialog': True,
                       'ordering': 70.0,
                       'permissions': (ZEN_CHANGE_DEVICE,)},
                    {  'action': 'dialog_moveDevices',
                        'banned_classes': ['Monitor'],
                        'description': 'Move to Class...',
                        'id': 'moveclass',
                        'isdialog': True,
                        'ordering': 50.0,
                        'permissions': (ZEN_CHANGE_DEVICE,)},
                     {  'action': 'dialog_setGroups',
                        'banned_classes': ['Monitor'],
                        'description': 'Set Groups...',
                        'id': 'setGroups',
                        'isdialog': True,
                        'ordering': 40.0,
                        'permissions': (ZEN_CHANGE_DEVICE,)},
                     {  'action': 'dialog_setSystems',
                        'banned_classes': ['Monitor'],
                        'description': 'Set Systems...',
                        'id': 'setSystems',
                        'isdialog': True,
                        'ordering': 30.0,
                        'permissions': (ZEN_CHANGE_DEVICE,)},
                     {  'action': 'dialog_setLocation',
                        'banned_classes': ['Monitor'],
                        'description': 'Set Location...',
                        'id': 'setLocation',
                        'isdialog': True,
                        'ordering': 20.0,
                        'permissions': (ZEN_CHANGE_DEVICE,)},
                    {  'action': 'dialog_setPerformanceMonitor',
                       'banned_classes': ['StatusMonitorConf'],
                       'description': 'Set Perf Monitor...',
                       'id': 'setPerformanceMonitor',
                       'isdialog': True,
                       'ordering': 15.0,
                       'permissions': (ZEN_CHANGE_DEVICE,)},
                     {  'action': 'dialog_removeDevices',
                        'description': 'Delete devices...',
                        'id': 'removeDevices',
                        'isdialog': True,
                        'ordering': 10.0,
                        'permissions': (ZEN_CHANGE_DEVICE,)},
                     {  'action': 'dialog_lockDevices',
                        'banned_classes': ['Monitor'],
                        'description': 'Lock devices...',
                        'id': 'lockDevices',
                        'isdialog': True,
                        'ordering': 2.0,
                        'permissions': (ZEN_CHANGE_DEVICE,)},
                     {  'action': 'dialog_setStatusMonitors',
                        'banned_classes': ['PerformanceConf'],
                        'description': 'Set Status Monitors...',
                        'id': 'setStatusMonitors',
                        'isdialog': True,
                        'ordering': 11.0,
                        'permissions': (ZEN_CHANGE_DEVICE,),
                    }],
        })

BanClassesOnDeviceListMenus()