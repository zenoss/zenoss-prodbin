#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
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

ZenPackItem = dict(
    id=         'addToZenPack',
    description='Add to ZenPack...',
    action=     'dialog_addToZenPack',
    permissions=('View',),
    isdialog = True,
    )

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
 dict(
            id=         'addToZenPack',
            description='Add to ZenPack...',
            action=     'dialog_addToZenPack',
            permissions=('View',),
            isdialog = True,
            allowed_classes = ['ZenPackable'],
            ),
 {'action': 'dialog_lock',
  'allowed_classes': ['Device',
                       'WinService'
                       'FileSystem',
                       'HardDisk',
                       'IpInterface',
                       'IpService',
                       'OSProcess',
                       'IpRouteEntry'],
  'description': 'Lock',
  'id': 'lockObject',
  'isdialog': True,
  'permissions': ('Change Device',)},
 {'action': 'dialog_delete',
  'allowed_classes': ['Device',
                    'WinService'
                    'FileSystem',
                    'HardDisk',
                    'IpInterface',
                    'IpService',
                    'OSProcess',
                    'IpRouteEntry'],
  'description': 'Delete',
  'id': 'deleteObject',
  'isdialog': True,
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
            'Organizer_list':            [
                ZenPackItem,
                dict(
                    id=         'addOrganizer',
                    description='Add New Organizer...',
                    action=     'dialog_addOrganizer',
                    permissions=('Manage DMD',),
                    isdialog=   True,
                    ),
                dict(
                    id=         'moveOrganizer',
                    description='Move Organizers...',
                    action=     'dialog_moveOrganizer',
                    permissions=('Manage DMD',),
                    isdialog=   True,
                    ),
                dict(
                    id=         'removeOrganizers',
                    description='Delete Organizers...',
                    action=     'dialog_removeOrganizer',
                    permissions=('Manage DMD',),
                    isdialog = True
                    ),
            ],
            'Service_list':                    [
                ZenPackItem,
                dict(
                    id=         'addServiceClass',
                    description='Add Service...',
                    action=     'dialog_addServiceClass',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'removeServiceClasses',
                    description='Delete Services...',
                    action=     'dialog_removeServiceClasses',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'moveServiceClasses',
                    description='Move Services...',
                    action=     'dialog_moveServiceClasses',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                    ],
            'OSProcess_list': [
                ZenPackItem,
                dict(
                    id=         'addOSProcess',
                    description='Add Process...',
                    action=     'dialog_addOSProcess',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'removeOSProcesses',
                    description='Delete Processes...',
                    action=     'dialog_removeOSProcesses',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'moveOSProcesses',
                    description='Move Processes...',
                    action=     'dialog_moveOSProcesses',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                    ],
            'Manufacturer_list':               [
                ZenPackItem,
                dict(
                    id=         'addManufacturer',
                    description='Add Manufacturer...',
                    action=     'dialog_addManufacturer',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'removeManufacturers',
                    description='Delete Manufacturers...',
                    action=     'dialog_removeManufacturers',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                ],
            'Mib_list':                    [
                ZenPackItem,
                dict(
                    id=         'addMibModule',
                    description='Add Mib...',
                    action=     'dialog_addMibModule',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'removeMibModules',
                    description='Delete Mibs...',
                    action=     'dialog_removeMibModules',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'moveMibModules',
                    description='Move Mibs...',
                    action=     'dialog_moveMibModules',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                    ],
            'EventMapping_list':               [
                ZenPackItem,
                dict(
                    id=         'addInstance',
                    description='Add Mapping...',
                    action=     'dialog_createInstance',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'removeInstances',
                    description='Delete Mappings...',
                    action=     'dialog_removeInstances',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'moveInstances',
                    description='Move Mappings...',
                    action=     'dialog_moveInstances',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                    ],
            'PerformanceMonitor_list': [
                ZenPackItem,
                dict(
                    id=         'addPMonitor',
                    description='Add Monitor...',
                    action=     'dialog_addMonitor',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'removePMonitors',
                    description='Delete Monitors...',
                    action=     'dialog_removeMonitors',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                ],
            'StatusMonitor_list': [
                ZenPackItem,
                dict(
                    id=         'addSMonitor',
                    description='Add Monitor...',
                    action=     'dialog_addMonitor',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'removeSMonitors',
                    description='Delete Monitors...',
                    action=     'dialog_removeMonitors',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                ],
            # doesn't work:
            # 'ReportClass_list':                [ZenPackItem],
            'ZenPack_list':[
                dict(
                    id=         'addZenPack',
                    description='Create a new ZenPack...',
                    action=     'dialog_addZenPack',
                    permissions=('Manage DMD',),
                    isdialog = True,
                    ),
                dict(
                    id=         'removeZenPack',
                    description='Delete ZenPack',
                    permissions=('Manage DMD',),
                    action=     'dialog_removeZenPacks',
                    isdialog=True,
                    ),
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
                    ),
                dict(
                    id=         'lockDevices',
                    description='Change lock...',
                    action=     'dialog_lockDevices',
                    permissions=('Change Device',),
                    isdialog = True
                    )
                ],
            'IpInterface':[
                dict(
                    id=         'addIpInterface',
                    description='Add IpInterface...',
                    action=     'dialog_addIpInterface',
                    isdialog = True,
                    permissions=('Change Device',),
                    )
                ],
            'OSProcess':[
                dict(
                    id=         'addOSProcess',
                    description='Add OSProcess...',
                    action=     'dialog_addOSProcess',
                    isdialog = True,
                    permissions=('Change Device',),
                    )
                ],
            'FileSystem':[
                dict(
                    id=         'addFileSystem',
                    description='Add File System...',
                    action=     'dialog_addFileSystem',
                    isdialog = True,
                    permissions=('Change Device',),
                    )
                ],
            'IpRouteEntry':[
                dict(
                    id=         'addIpRouteEntry',
                    description='Add Route...',
                    action=     'dialog_addIpRouteEntry',
                    isdialog = True,
                    permissions=('Change Device',),
                    )
                ],
            'Event_list':[
                dict(
                    id=         'acknowledgeEvents',
                    description='Acknowledge Events',
                    action=     ('javascript:submitFormToMethod('
                                 '"control", "manage_ackEvents")'),
                    permissions=('Manage DMD',)
                    ),
                dict(
                    id=         'historifyEvents',
                    description='Move Events to History...',
                    action=     'dialog_moveEventsToHistory',
                    permissions=('Manage DMD',),
                    isdialog=   True
                    ),
                dict(
                    id=         'exportAllEvents',
                    description='Download as CSV',
                    action=     'javascript:goExport()',
                    permissions=('View',)
                    ),
                dict(
                    id=         'createEventMap',
                    description='Map Events to Class...',
                    action=     'dialog_createEventMap',
                    permissions=('Manage DMD',),
                    isdialog=   True
                    ),
            ],
            'HistoryEvent_list':[
                dict(
                    id=         'createEventMap',
                    description='Map Events to Class...',
                    action=     'dialog_createEventMap',
                    permissions=('Manage DMD',),
                    isdialog=   True
                    ),
                dict(
                    id=         'exportAllEvents',
                    description='Download as CSV',
                    action=     'javascript:goExport()',
                    permissions=('View',)
                    ),
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
