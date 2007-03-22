#################################################################
# #   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Add menu relations to all device organizers, OsProcesses, Services, etc
Add default menus to dmd and device organizers

$Id:$
'''
import Migrate
import os
from Products.ZenRelations.ImportRM import ImportRM
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.Device import Device

zenhome = os.environ['ZENHOME']
menuxml = os.path.join(zenhome, "Products/ZenModel/data/menus.xml")

class MenuRelations(Migrate.Step):
    version = Migrate.Version(1, 2, 0)

    def cutover(self, dmd):
        dmd.buildRelations()
#        for dev in dmd.Devices.getSubDevices():
#            dev.buildRelations()
#        for name in ['Devices', 'Systems', 'Groups', 'Locations',
#                        'Services', 'Processes']:
#            top = getattr(dmd, name)
#            orgs = top.getSubOrganizers()
#            orgs.insert(0, top)
#            for o in orgs:
#                o.buildRelations()
#                if name == 'Devices':
#                    for d in o.devices():
#                        d.buildRelations()
#                        if getattr(d, 'os', None):
#                            for n in ['ipservices', 'winservices', 'processes']:
#                                for p in getattr(d.os, n)():
#                                    p.buildRelations()
#                if name == 'Services':
#                    for sc in o.serviceclasses():
#                        sc.buildRelations()
#                if name == 'Processes':
#                    for pc in o.osProcessClasses():
#                        pc.buildRelations()

        # Add menus.
        
# Get rid of all menus

        hasmenus = lambda x: hasattr(x, 'zenMenus') 
        if hasmenus(dmd): dmd.zenMenus.removeRelation()
        if hasmenus(dmd.Devices): dmd.Devices.zenMenus.removeRelation()
        if hasmenus(dmd.Networks): dmd.Networks.zenMenus.removeRelation()

        dmd.buildMenus(
            {'Edit':[
 {'action': 'objRRDTemplate',
  'allowed_classes': ['Device',
                      'FileSystem',
                      'HardDisk',
                      'IpInterface',
                      'OSProcess'],
  'description': 'PerfConf',
  'id': 'objRRDTemplate',
  'permissions': ('Change Device',)},
 {'action': 'editStatusMonitorConf',
  'allowed_classes': ['StatusMonitorConf'],
  'description': 'Edit',
  'id': 'editStatusMonitorConf',
  'permissions': ('Manage DMD',)},
 {'action': 'deviceCustomEdit',
  'allowed_classes': ['Device'],
  'description': 'Custom',
  'id': 'deviceCustomEdit',
  'permissions': ('View',)},
 {'action': 'eventClassInstEdit',
  'allowed_classes': ['EventClassInst'],
  'description': 'Edit',
  'id': 'eventClassInstEdit',
  'permissions': ('Manage DMD',)},
 {'action': 'ipServiceClassEdit',
  'allowed_classes': ['IpServiceClass'],
  'description': 'Edit',
  'id': 'ipServiceClassEdit',
  'permissions': ('Manage DMD',)},
 {'action': 'deviceManagement',
  'allowed_classes': ['Device'],
  'description': 'Manage',
  'id': 'deviceManagement',
  'permissions': ('Change Device',)},
 {'action': 'serviceOrganizerManage',
  'allowed_classes': ['ServiceOrganizer'],
  'description': 'Manage',
  'id': 'serviceOrganizerManage',
  'permissions': ('Manage DMD',)},
 {'action': 'osProcessOrganizerManage',
  'allowed_classes': ['OSProcessOrganizer'],
  'description': 'Manage',
  'id': 'osProcessOrganizerManage',
  'permissions': ('Manage DMD',)},
 {'action': 'ipServiceClassManage',
  'allowed_classes': ['IpServiceClass'],
  'description': 'Manage',
  'id': 'ipServiceClassManage',
  'permissions': ('Manage DMD',)},
 {'action': 'editManufacturer',
  'allowed_classes': ['Manufacturer'],
  'description': 'Edit',
  'id': 'editManufacturer',
  'permissions': ('Manage DMD',)},
 {'action': 'osProcessManage',
  'allowed_classes': ['OSProcess'],
  'description': 'Manage',
  'id': 'osProcessManage',
  'permissions': ('Manage DMD',)},
 {'action': 'serviceClassManage',
  'allowed_classes': ['ServiceClass'],
  'description': 'Manage',
  'id': 'serviceClassManage',
  'permissions': ('Manage DMD',)},
 {'action': 'editPerformanceConf',
  'allowed_classes': ['PerformanceConf'],
  'description': 'Edit',
  'id': 'editPerformanceConf',
  'permissions': ('Manage DMD',)},
 {'action': 'ipServiceManage',
  'allowed_classes': ['IpService'],
  'description': 'Manage',
  'id': 'ipServiceManage',
  'permissions': ('Manage DMD',)},
 {'action': 'editProductClass',
  'allowed_classes': ['ProductClass'],
  'description': 'Edit',
  'id': 'editProductClass',
  'permissions': ('Manage DMD',)},
 {'action': 'osProcessClassManage',
  'allowed_classes': ['OSProcessClass'],
  'description': 'Manage',
  'id': 'osProcessClassManage',
  'permissions': ('Manage DMD',)},
 {'action': 'deviceOrganizerManage',
  'allowed_classes': ['DeviceOrganizer',
                      'DeviceGroup',
                      'Location',
                      'DeviceClass', 
                      'System'],
  'description': 'Manage',
  'id': 'deviceOrganizerManage',
  'permissions': ('Manage DMD',)},
 {'action': 'editDevice',
  'allowed_classes': ['Device'],
  'description': 'Edit',
  'id': 'editDevice',
  'permissions': ('Change Device',)},
 {'action': 'winServiceManage',
  'allowed_classes': ['WinService'],
  'description': 'Manage',
  'id': 'winServiceManage',
  'permissions': ('Manage DMD',)},
 {'action': 'eventClassInstSequence',
  'allowed_classes': ['EventClassInst'],
  'description': 'Sequence',
  'id': 'eventClassInstSequence',
  'permissions': ('View',)},
 {'action': 'osProcessClassEdit',
  'allowed_classes': ['OSProcessClass'],
  'description': 'Edit',
  'id': 'osProcessClassEdit',
  'permissions': ('Manage DMD',)},
 {'action': 'perfConfig',
  'allowed_classes': ['DeviceClass'],
  'description': 'Perf Config',
  'id': 'perfConfig',
  'permissions': ('Change Device',)},
 {'action': 'zPropertyEdit',
  'allowed_classes': ['Device',
                      'DeviceClass',
                      'IpNetwork',
                      'IpServiceClass',
                      'Manufacturer',
                      'OSProcessClass',
                      'OSProcessOrganizer',
                      'ProductClass',
                      'ServiceClass',
                      'ServiceOrganizer',
                      'EventClassInst',
                      'EventClass'],
  'description': 'zProperties',
  'id': 'zPropertyEdit',
  'permissions': ('View',)},
 {'action': 'serviceClassEdit',
  'allowed_classes': ['ServiceClass'],
  'description': 'Edit',
  'id': 'serviceClassEdit',
  'permissions': ('Manage DMD',)},
],
            'DeviceOrganizer_list':[
                dict(
                    id=         'addToZenPack',
                    description='Add to ZenPack...',
                    action=     'dialog_addToZenPack',
                    permissions=('View',),
                    isdialog = True
                    )
                ],
            'Device_list':[
                dict(
                    id=         'moveclass',
                    description='Move to Class...',
                    action=     'dialog_moveDevices',
                    permissions=('Change Device',),
                    isdialog = True
                    ),
                dict(
                    id=         'setGroups',
                    description='Set Groups...',
                    action=     'dialog_setGroups',
                    permissions=('Change Device',),
                    isdialog = True
                    ),
                dict(
                    id=         'setSystems',
                    description='Set Systems...',
                    action=     'dialog_setSystems',
                    permissions=('Change Device',),
                    isdialog = True
                    ),
                dict(
                    id=         'setLocation',
                    description='Set Location...',
                    action=     'dialog_setLocation',
                    permissions=('Change Device',),
                    isdialog = True
                    ),
                dict(
                    id=         'removeDevices',
                    description='Delete devices...',
                    action=     'dialog_removeDevices',
                    permissions=('Change Device',),
                    isdialog = True
                    )
                ],
            'HistoryEvent_list':[
                dict(
                    id=         'undeleteHistoryEvents',
                    description='Undelete Events...',
                    action=     'dialog_undeleteHistoryEvents',
                    permissions=('Manage DMD',),
                    isdialog = True
                    )
                ],
            })


        dmd.Networks.buildMenus(
            {'Actions':[
                dict(
                    id=             'discover',
                    description=    'Discover Devices', 
                    action=         'discoverDevices', 
                    allowed_classes= ('IpNetwork',)
                    ),
                ]
            })
            
MenuRelations()
