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

ZenPackItems = dict(
    ordering=0.0, 
    id=         'addToZenPack',
    description='Add to ZenPack...',
    action=     'dialog_addToZenPack',
    permissions=('View',),
    isdialog=True,
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
            {
            'Edit':[
                dict(action='viewHistory',
                    allowed_classes=['Device',
                    'DeviceClass',
                    'EventClass',
                    'EventClassInst',
                    'DeviceOrganizer',],
                    description='Changes',
                    ordering=0.0,
                    id='viewHistory',
                    permissions=('Change Device',)
                    ),
                dict(action='objRRDTemplate',
                    allowed_classes=['Device',
                    'FileSystem',
                    'HardDisk',
                    'IpInterface',
                    'OSProcess'],
                    description='PerfConf',
                    ordering=1.0,
                    id='objRRDTemplate',
                    permissions=('Change Device',)
                    ),
                dict(action='../objRRDTemplate',
                    allowed_classes=['OperatingSystem'],
                    description='PerfConf',
                    ordering=1.0, 
                    id='objRRDTemplate_os',
                    permissions=('Change Device',)
                    ),
                dict(
                    ordering=2.0, 
                    id=         'addToZenPack',
                    description='Add to ZenPack...',
                    action=     'dialog_addOneToZenPack',
                    permissions=('View',),
                    isdialog=True,
                    allowed_classes = ['ZenPackable'],
                    ),
                dict(action='dialog_lock',
                    allowed_classes=['Device',
                    'OperatingSystem',
                    'WinService',
                    'FileSystem',
                    'HardDisk',
                    'IpInterface',
                    'IpService',
                    'OSProcess',
                    'IpRouteEntry'],
                    description='Lock',
                    ordering=3.0, 
                    id='lockObject',
                    isdialog=True,
                    permissions=('Change Device',)
                    ),
                dict(action='dialog_deleteComponent',
                    allowed_classes=['WinService',
                    'FileSystem',
                    'HardDisk',
                    'IpInterface',
                    'IpService',
                    'OSProcess',
                    'IpRouteEntry'],
                    description='Delete',
                    ordering=4.0, 
                    id='deleteObject',
                    isdialog=True,
                    permissions=('Change Device',)
                    ),
                dict(action='pushConfig',
                    allowed_classes=['DeviceClass', 
                        'Device'],
                    description='Push Changes',
                    ordering=6.0, 
                    id='pushConfig',
                    permissions=('Change Device',)
                    ),
                dict(action='../pushConfig',
                    allowed_classes=['OperatingSystem'],
                    description='Push Changes',
                    ordering=7.0, 
                    id='pushConfig_os',
                    permissions=('Change Device',)
                    ),
                dict(action='deviceCustomEdit',
                    allowed_classes=['Device'],
                    description='Custom',
                    ordering=8.0, 
                    id='deviceCustomEdit',
                    permissions=('View',)
                    ),
                dict(action='../deviceCustomEdit',
                    allowed_classes=['OperatingSystem'],
                    description='Custom',
                    ordering=9.0, 
                    id='deviceCustomEdit_os',
                    permissions=('View',)
                    ),
                dict(action='deviceManagement',
                    allowed_classes=['Device'],
                    description='Manage',
                    ordering=12.0, 
                    id='deviceManagement',
                    permissions=('Change Device',)
                    ),
                dict(action='../deviceManagement',
                    allowed_classes=['OperatingSystem'],
                    description='Manage',
                    ordering=13.0, 
                    id='deviceManagement_os',
                    permissions=('Change Device',)
                    ),
                dict(action='serviceOrganizerManage',
                    allowed_classes=['ServiceOrganizer'],
                    description='Manage',
                    ordering=14.0, 
                    id='serviceOrganizerManage',
                    permissions=('Manage DMD',)
                    ),
                dict(action='osProcessOrganizerManage',
                    allowed_classes=['OSProcessOrganizer'],
                    description='Manage',
                    ordering=15.0, 
                    id='osProcessOrganizerManage',
                    permissions=('Manage DMD',)
                    ),
                dict(action='ipServiceClassManage',
                    allowed_classes=['IpServiceClass'],
                    description='Manage',
                    ordering=16.0, 
                    id='ipServiceClassManage',
                    permissions=('Manage DMD',)
                    ),
                dict(action='osProcessManage',
                    allowed_classes=['OSProcess'],
                    description='Manage',
                    ordering=18.0, 
                    id='osProcessManage',
                    permissions=('Manage DMD',)
                    ),
                dict(action='serviceClassManage',
                    allowed_classes=['ServiceClass'],
                    description='Manage',
                    ordering=19.0, 
                    id='serviceClassManage',
                    permissions=('Manage DMD',)
                    ),
                dict(action='ipServiceManage',
                    allowed_classes=['IpService'],
                    description='Manage',
                    ordering=21.0, 
                    id='ipServiceManage',
                    permissions=('Manage DMD',)
                    ),
                dict(action='osProcessClassManage',
                    allowed_classes=['OSProcessClass'],
                    description='Manage',
                    ordering=23.0, 
                    id='osProcessClassManage',
                    permissions=('Manage DMD',)
                    ),
                dict(action='deviceOrganizerManage',
                    allowed_classes=['DeviceOrganizer',
                    'DeviceGroup',
                    'Location',
                    'DeviceClass', 
                    'System'],
                    description='Manage',
                    ordering=24.0, 
                    id='deviceOrganizerManage',
                    permissions=('Manage DMD',)
                    ),                    
                dict(action='winServiceManage',
                    allowed_classes=['WinService'],
                    description='Manage',
                    ordering=27.0, 
                    id='winServiceManage',
                    permissions=('Manage DMD',)
                    ),
                dict(action='editStatusMonitorConf',
                    allowed_classes=['StatusMonitorConf'],
                    description='Edit',
                    ordering=5.0, 
                    id='editStatusMonitorConf',
                    permissions=('Manage DMD',)
                    ),
                dict(action='editManufacturer',
                    allowed_classes=['Manufacturer'],
                    description='Edit',
                    ordering=17.0, 
                    id='editManufacturer',
                    permissions=('Manage DMD',)
                    ),
                dict(action='editPerformanceConf',
                    allowed_classes=['PerformanceConf'],
                    description='Edit',
                    ordering=20.0, 
                    id='editPerformanceConf',
                    permissions=('Manage DMD',)
                    ),
                dict(action='editProductClass',
                    allowed_classes=['ProductClass'],
                    description='Edit',
                    ordering=22.0, 
                    id='editProductClass',
                    permissions=('Manage DMD',)
                    ),
                dict(action='eventClassInstSequence',
                    allowed_classes=['EventClassInst'],
                    description='Sequence',
                    ordering=28.0, 
                    id='eventClassInstSequence',
                    permissions=('View',)
                    ),
                dict(action='performanceTemplates',
                    allowed_classes=['DeviceClass'],
                    description='All Templates',
                    ordering=30.0, 
                    id='performanceTemplates',
                    permissions=('View Device',)
                    ),
                dict(action='perfConfig',
                    allowed_classes=['DeviceClass'],
                    description='Available Templates',
                    ordering=31.0, 
                    id='perfConfig',
                    permissions=('Change Device',)
                    ),
                dict(action='zPropertyEdit',
                    allowed_classes=['Device',
                    'Manufacturer',
                    'ProductClass',
                    ],
                    description='zProperties',
                    ordering=32.0, 
                    id='zPropertyEdit',
                    permissions=('View',)
                    ),
                dict(action='../zPropertyEdit',
                    allowed_classes=['OperatingSystem'],
                    description='zProperties',
                    ordering=33.0, 
                    id='zPropertyEdit_os',
                    permissions=('View',)
                    ),
                ],
            'Organizer_list':            [
                ZenPackItems,
                dict(
                    ordering=1.0, 
                    id=         'addOrganizer',
                    description='Add New Organizer...',
                    action=     'dialog_addOrganizer',
                    permissions=('Manage DMD',),
                    isdialog=   True,
                    ),
                dict(
                    ordering=2.0, 
                    id=         'moveOrganizer',
                    description='Move Organizers...',
                    action=     'dialog_moveOrganizer',
                    permissions=('Manage DMD',),
                    isdialog=   True,
                    ),
                dict(
                    ordering=3.0, 
                    id=         'removeOrganizers',
                    description='Delete Organizers...',
                    action=     'dialog_removeOrganizer',
                    permissions=('Manage DMD',),
                    isdialog=True
                    ),
            ],
            'Service_list':                    [
                ZenPackItems,
                dict(
                    ordering=1.0, 
                    id=         'addServiceClass',
                    description='Add Service...',
                    action=     'dialog_addServiceClass',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    ordering=2.0, 
                    id=         'removeServiceClasses',
                    description='Delete Services...',
                    action=     'dialog_removeServiceClasses',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    ordering=3.0, 
                    id=         'moveServiceClasses',
                    description='Move Services...',
                    action=     'dialog_moveServiceClasses',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                    ],
            'OSProcess_list': [
                ZenPackItems,
                dict(
                    ordering=1.0, 
                    id=         'addOSProcess',
                    description='Add Process...',
                    action=     'dialog_addOSProcess',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    ordering=2.0, 
                    id=         'removeOSProcesses',
                    description='Delete Processes...',
                    action=     'dialog_removeOSProcesses',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    ordering=3.0, 
                    id=         'moveOSProcesses',
                    description='Move Processes...',
                    action=     'dialog_moveOSProcesses',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                    ],
            'Manufacturer_list':               [
                ZenPackItems,
                dict(
                    ordering=1.0, 
                    id=         'addManufacturer',
                    description='Add Manufacturer...',
                    action=     'dialog_addManufacturer',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    ordering=2.0, 
                    id=         'removeManufacturers',
                    description='Delete Manufacturers...',
                    action=     'dialog_removeManufacturers',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                ],
            'Mib_list':                    [
                ZenPackItems,
                dict(
                    ordering=1.0, 
                    id=         'addMibModule',
                    description='Add Mib...',
                    action=     'dialog_addMibModule',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    ordering=2.0, 
                    id=         'removeMibModules',
                    description='Delete Mibs...',
                    action=     'dialog_removeMibModules',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    ordering=3.0, 
                    id=         'moveMibModules',
                    description='Move Mibs...',
                    action=     'dialog_moveMibModules',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                    ],
            'EventMapping_list':               [
                ZenPackItems,
                dict(
                    ordering=1.0, 
                    id=         'addInstance',
                    description='Add Mapping...',
                    action=     'dialog_createInstance',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    ordering=2.0, 
                    id=         'removeInstances',
                    description='Delete Mappings...',
                    action=     'dialog_removeInstances',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    ordering=3.0, 
                    id=         'moveInstances',
                    description='Move Mappings...',
                    action=     'dialog_moveInstances',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                    ],
            'PerformanceMonitor_list': [
                dict(
                    ordering=1.0, 
                    id=         'addPMonitor',
                    description='Add Monitor...',
                    action=     'dialog_addMonitor',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    ordering=2.0, 
                    id=         'removePMonitors',
                    description='Delete Monitors...',
                    action=     'dialog_removeMonitors',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                ],
            'StatusMonitor_list': [
                dict(
                    ordering=1.0, 
                    id=         'addSMonitor',
                    description='Add Monitor...',
                    action=     'dialog_addMonitor',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    ordering=2.0, 
                    id=         'removeSMonitors',
                    description='Delete Monitors...',
                    action=     'dialog_removeMonitors',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                ],
            'ReportClass_list': [
                ZenPackItems
                ],
            'ZenPack_list':[
                dict(
                    ordering=1.0, 
                    id=         'addZenPack',
                    description='Create a new ZenPack...',
                    action=     'dialog_addZenPack',
                    permissions=('Manage DMD',),
                    isdialog=True,
                    ),
                dict(
                    ordering=2.0, 
                    id=         'removeZenPack',
                    description='Delete ZenPack',
                    permissions=('Manage DMD',),
                    action=     'dialog_removeZenPacks',
                    isdialog=True,
                    ),
                ],
            'Device_list':[
                dict(
                    ordering=1.0, 
                    id=         'moveclass',
                    description='Move to Class...',
                    action=     'dialog_moveDevices',
                    permissions=('Change Device',),
                    isdialog=True
                    ),
                dict(
                    ordering=2.0, 
                    id=         'setGroups',
                    description='Set Groups...',
                    action=     'dialog_setGroups',
                    permissions=('Change Device',),
                    isdialog=True
                    ),
                dict(
                    ordering=3.0, 
                    id=         'setSystems',
                    description='Set Systems...',
                    action=     'dialog_setSystems',
                    permissions=('Change Device',),
                    isdialog=True
                    ),
                dict(
                    ordering=4.0, 
                    id=         'setLocation',
                    description='Set Location...',
                    action=     'dialog_setLocation',
                    permissions=('Change Device',),
                    isdialog=True
                    ),
                dict(
                    ordering=5.0, 
                    id=         'removeDevices',
                    description='Delete devices...',
                    action=     'dialog_removeDevices',
                    permissions=('Change Device',),
                    isdialog=True
                    ),
                dict(
                    ordering=6.0, 
                    id=         'lockDevices',
                    description='Lock devices...',
                    action=     'dialog_lockDevices',
                    permissions=('Change Device',),
                    isdialog=True
                    )
                ],
            'IpInterface':[
                dict(
                    ordering=1.0, 
                    id=         'addIpInterface',
                    description='Add IpInterface...',
                    action=     'dialog_addIpInterface',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    ordering=2.0, 
                    id=         'deleteIpInterfaces',
                    description='Delete IpInterfaces...',
                    action=     'dialog_deleteIpInterfaces',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    ordering=3.0, 
                    id=         'lockIpInterfaces',
                    description='Lock IpInterfaces...',
                    action=     'dialog_lockIpInterfaces',
                    isdialog=True,
                    permissions=('Change Device',),
                    )
                ],
            'OSProcess':[
                dict(
                    ordering=1.0, 
                    id=         'addOSProcess',
                    description='Add OSProcess...',
                    action=     'dialog_addOSProcess',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    ordering=2.0, 
                    id=         'deleteOSProcesses',
                    description='Delete OSProcesses...',
                    action=     'dialog_deleteOSProcesses',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    ordering=3.0, 
                    id=         'lockOSProcesses',
                    description='Lock OSProcesses...',
                    action=     'dialog_lockOSProcesses',
                    isdialog=True,
                    permissions=('Change Device',),
                    )
                ],
            'FileSystem':[
                dict(
                    ordering=1.0, 
                    id=         'addFileSystem',
                    description='Add File System...',
                    action=     'dialog_addFileSystem',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    ordering=2.0, 
                    id=         'deleteFileSystems',
                    description='Delete FileSystems...',
                    action=     'dialog_deleteFileSystems',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    ordering=3.0, 
                    id=         'lockFileSystems',
                    description='Lock FileSystems...',
                    action=     'dialog_lockFileSystems',
                    isdialog=True,
                    permissions=('Change Device',),
                    )
                ],
            'IpRouteEntry':[
                dict(
                    ordering=1.0, 
                    id=         'addIpRouteEntry',
                    description='Add IpRouteEntry...',
                    action=     'dialog_addIpRouteEntry',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    ordering=2.0, 
                    id=         'deleteIpRouteEntries',
                    description='Delete IpRouteEntries...',
                    action=     'dialog_deleteIpRouteEntries',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    ordering=3.0, 
                    id=         'lockIpRouteEntries',
                    description='Lock IpRouteEntries...',
                    action=     'dialog_lockIpRouteEntries',
                    isdialog=True,
                    permissions=('Change Device',),
                    )
                ],
            'IpService':[
                dict(
                    ordering=1.0, 
                    id=         'addIpService',
                    description='Add IpService...',
                    action=     'dialog_addIpService',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    ordering=2.0, 
                    id=         'deleteIpServices',
                    description='Delete IpServices...',
                    action=     'dialog_deleteIpServices',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    ordering=3.0, 
                    id=         'lockIpServices',
                    description='Lock IpServices...',
                    action=     'dialog_lockIpServices',
                    isdialog=True,
                    permissions=('Change Device',),
                    )
                ],
            'WinService':[
                dict(
                    ordering=1.0, 
                    id=         'addWinService',
                    description='Add WinService...',
                    action=     'dialog_addWinService',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    ordering=2.0, 
                    id=         'deleteWinServices',
                    description='Delete WinServices...',
                    action=     'dialog_deleteWinServices',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    ordering=3.0, 
                    id=         'lockWinServices',
                    description='Lock WinServices...',
                    action=     'dialog_lockWinServices',
                    isdialog=True,
                    permissions=('Change Device',),
                    )
                ],
            'Event_list':[
                dict(
                    ordering=1.0, 
                    id=         'acknowledgeEvents',
                    description='Acknowledge Events',
                    action=     ('javascript:submitFormToMethod('
                                 '"control", "manage_ackEvents")'),
                    permissions=('Manage DMD',)
                    ),
                dict(
                    ordering=2.0, 
                    id=         'historifyEvents',
                    description='Move Events to History...',
                    action=     'dialog_moveEventsToHistory',
                    permissions=('Manage DMD',),
                    isdialog=   True
                    ),
                dict(
                    ordering=3.0, 
                    id=         'exportAllEvents',
                    description='Download as CSV',
                    action=     'javascript:goExport()',
                    permissions=('View',)
                    ),
                dict(
                    ordering=4.0, 
                    id=         'createEventMap',
                    description='Map Events to Class...',
                    action=     'dialog_createEventMap',
                    permissions=('Manage DMD',),
                    isdialog=   True
                    ),
            ],
            'HistoryEvent_list':[
                dict(
                    ordering=1.0, 
                    id=         'createEventMap',
                    description='Map Events to Class...',
                    action=     'dialog_createEventMap',
                    permissions=('Manage DMD',),
                    isdialog=   True
                    ),
                dict(
                    ordering=2.0, 
                    id=         'exportAllEvents',
                    description='Download as CSV',
                    action=     'javascript:goExport()',
                    permissions=('View',)
                    ),
                dict(
                    ordering=3.0, 
                    id=         'undeleteHistoryEvents',
                    description='Undelete Events...',
                    action=     'dialog_undeleteHistoryEvents',
                    permissions=('Manage DMD',),
                    isdialog=True
                    )
                ],
            'DataSource_list':[
                dict(
                    ordering=1.0, 
                    id = 'addDataSource',
                    description = 'Add DataSource...',
                    action = 'dialog_addDataSource',
                    permissions= ('Change Device',),
                    isdialog=True,
                    ),
                dict(
                    ordering=2.0, 
                    id = 'deleteDataSource',
                    description = 'Delete DataSource...',
                    action = 'dialog_deleteDataSource',
                    permissions= ('Change Device',),
                    isdialog=True,
                    ),
                ],
            'DataPoint_list':[
                dict(
                    ordering=1.0, 
                    id = 'addDataPoint',
                    description = 'Add DataPoint...',
                    action = 'dialog_addDataPoint',
                    permissions= ('Change Device',),
                    isdialog=True,
                    ),
                dict(
                    ordering=2.0, 
                    id = 'deleteDataPoint',
                    description = 'Delete DataPoint...',
                    action = 'dialog_deleteDataPoint',
                    permissions= ('Change Device',),
                    isdialog=True,
                    ),
                ],
            'Threshold_list':[
                dict(
                    ordering=1.0, 
                    id = 'addThreshold',
                    description = 'Add Threshold...',
                    action = 'dialog_addThreshold',
                    permissions= ('Change Device',),
                    isdialog=True,
                    ),
                dict(
                    ordering=2.0, 
                    id = 'deleteThreshold',
                    description = 'Delete Threshold...',
                    action = 'dialog_deleteThreshold',
                    permissions= ('Change Device',),
                    isdialog=True,
                    ),
                ],
            'Graph_list':[
                dict(
                    ordering=1.0, 
                    id = 'addGraph',
                    description = 'Add Graph...',
                    action = 'dialog_addGraph',
                    permissions= ('Change Device',),
                    isdialog=True,
                    ),
                dict(
                    ordering=2.0, 
                    id = 'deleteGraph',
                    description = 'Delete Graph...',
                    action = 'dialog_deleteGraph',
                    permissions= ('Change Device',),
                    isdialog=True,
                    ),
                dict(
                    ordering=3.0, 
                    id = 'resequenceGraphs',
                    description = 'Re-sequence Graphs',
                    action = 'manage_resequenceRRDGraphs',
                    permissions= ('Change Device',),
                    isdialog=True,
                    ),
                ],
            'Subnetworks':[
                dict(
                    ordering=1.0, 
                    id=         'deleteNetwork',
                    description='Delete Networks...',
                    action=     'dialog_deleteNetwork',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    ordering=2.0, 
                    id=         'addNetwork',
                    description='Add Network...',
                    action=     'dialog_addNetwork',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                ],
            'IpAddresses':[
                dict(
                    ordering=1.0, 
                    id=         'deleteIpAddress',
                    description='Delete IpAddresses...',
                    action=     'dialog_deleteIpAddress',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                ],       
            'Manage': [
                dict(
                    ordering=1.0, 
                    id=         'changeClass',
                    description='Change Class',
                    action=     'dialog_changeClass',
                    isdialog=True,
                    permissions=('Change Device',),
                    allowed_classes = ('Device','OperatingSystem'),
                    ),
                dict(
                    ordering=2.0, 
                    id=         'setProductionState',
                    description='Set Production State',
                    action=     'dialog_setProductionState',
                    permissions=('Change Device',),
                    isdialog=True,
                    allowed_classes = ('Device','OperatingSystem','DeviceClass','DeviceGroup','Location','System'),
                    ),
                dict(
                    ordering=2.0, 
                    id=         'setPriority',
                    description='Set Priority',
                    action=     'dialog_setPriority',
                    isdialog=True,
                    permissions=('Change Device',),
                    allowed_classes = ('Device','OperatingSystem','DeviceClass','DeviceGroup','Location','System'),
                    ),
                dict(
                    ordering=2.0, 
                    id=         'modelDevice',
                    description='Model Device',
                    action=     'collectDevice',
                    permissions=('Change Device',),
                    allowed_classes = ('Device','OperatingSystem','DeviceClass','DeviceGroup','Location','System'),
                    ),
                dict(
                    ordering=3.0, 
                    id=         'resetIp',
                    description='Reset IP',
                    action=     'dialog_resetIp',
                    isdialog=True,
                    permissions=('Change Device',),
                    allowed_classes = ('Device','OperatingSystem','DeviceClass','DeviceGroup','Location','System'),
                    ),
                dict(
                    ordering=4.0, 
                    id=         'resetCommunity',
                    description='Reset Community',
                    action=     'manage_snmpCommunity',
                    permissions=('Change Device',),
                    allowed_classes = ('Device','OperatingSystem','DeviceClass','DeviceGroup','Location','System'),
                    ),
                dict(
                    ordering=5.0, 
                    id=         'renameDevice',
                    description='Rename Device',
                    action=     'dialog_renameDevice',
                    isdialog=True,
                    permissions=('Change Device',),
                    allowed_classes = ('Device','OperatingSystem'),
                    ),
                dict(
                    ordering=6.0, 
                    id=         'deleteDevice',
                    description='Delete Device',
                    action=     'dialog_deleteDevice',
                    isdialog=True,
                    permissions=('Change Device',),
                    allowed_classes = ('Device','OperatingSystem'),
                    ),
            ],             
            'Add': [
                dict(
                    ordering=1.0, 
                    id=         'addIpInterface',
                    description='Add IpInterface...',
                    action=     'dialog_addIpInterface',
                    isdialog=True,
                    permissions=('Change Device',),
                    allowed_classes = ('OperatingSystem',),
                    ),
                dict(
                    ordering=2.0, 
                    id=         'addOSProcess',
                    description='Add OSProcess...',
                    action=     'dialog_addOSProcess',
                    isdialog=True,
                    permissions=('Change Device',),
                    allowed_classes = ('OperatingSystem',),
                    ),
                dict(
                    ordering=3.0, 
                    id=         'addFileSystem',
                    description='Add File System...',
                    action=     'dialog_addFileSystem',
                    isdialog=True,
                    permissions=('Change Device',),
                    allowed_classes = ('OperatingSystem',),
                    ),
                dict(
                    ordering=4.0, 
                    id=         'addIpRouteEntry',
                    description='Add Route...',
                    action=     'dialog_addIpRouteEntry',
                    isdialog=True,
                    permissions=('Change Device',),
                    allowed_classes = ('OperatingSystem',),
                    ),
                dict(
                    ordering=5.0, 
                    id=         'addIpService',
                    description='Add IpService...',
                    action=     'dialog_addIpService',
                    isdialog=True,
                    permissions=('Change Device',),
                    allowed_classes = ('OperatingSystem',),
                    ),
                dict(
                    ordering=6.0, 
                    id=         'addWinService',
                    description='Add WinService...',
                    action=     'dialog_addWinService',
                    isdialog=True,
                    permissions=('Change Device',),
                    allowed_classes = ('OperatingSystem',),
                    ),
                dict(
                    ordering=7.0, 
                    id=         'addReportOrganizer',
                    description='Add Report Organizer...',
                    action=     'dialog_addReportClass',
                    isdialog=True,
                    permissions=('Change Device',),
                    allowed_classes = ('ReportClass',),
                    ),
                dict(
                    ordering=8.0, 
                    id=         'addDeviceReport',
                    description='Add Device Report...',
                    action=     'dialog_addReport',
                    isdialog=True,
                    permissions=('Change Device',),
                    allowed_classes = ('ReportClass',),
                    )
                ]
            })
        
        dmd.Networks.buildMenus(
            {'Actions':[
                dict(
                    ordering=1.0, 
                    id=             'discover',
                    description=    'Discover Devices', 
                    action=         'discoverDevices', 
                    allowed_classes= ('IpNetwork',)
                    )
                ]
            })
            
MenuRelations()
