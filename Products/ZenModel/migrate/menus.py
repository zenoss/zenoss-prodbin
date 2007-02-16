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

class MenuRelations(Migrate.Step):
    version = Migrate.Version(1, 2, 0)

    def cutover(self, dmd):
        dmd.buildRelations()
        for dev in dmd.Devices.getSubDevices():
            dev.buildRelations()
        for name in ['Devices', 'Systems', 'Groups', 'Locations',
                        'Services', 'Processes']:
            top = getattr(dmd, name)
            orgs = top.getSubOrganizers()
            orgs.insert(0, top)
            for o in orgs:
                o.buildRelations()
                if name == 'Devices':
                    for d in o.devices():
                        d.buildRelations()
                        if getattr(d, 'os', None):
                            for n in ['ipservices', 'winservices', 'processes']:
                                for p in getattr(d.os, n)():
                                    p.buildRelations()
                if name == 'Services':
                    for sc in o.serviceclasses():
                        sc.buildRelations()
                if name == 'Processes':
                    for pc in o.osProcessClasses():
                        pc.buildRelations()

        # Add menus.
        dmd.buildMenus(
            {'Edit':[
                dict(
                     id=         'manageob',
                     description='Manage',
                     action=     'dataRootManage',
                     permissions=('View',),
                     isglobal=   False
                    )
             ],
             'View':[
                dict(
                     id=         'viewHistory',
                     description='Changes',
                     action=     'viewHistory',
                     permissions=('View',)
                    )
             ]
            })


        dmd.Devices.buildMenus(
            {'Edit':[
                dict(
                     id=         'manageob',
                     description='Manage',
                     action=     'deviceOrganizerManage',
                     permissions=('View',)
                    ),
                dict(
                     id=         'editCustSchema',
                     description='Custom Schema',
                     action=     'editCustSchema',
                     permissions=('Change Device',)
                    ),
                dict(
                     id=         'perfConfig',
                     description='perfConf',
                     action=     'perfConfig',
                     permissions=('Change Device',),
                     allowed_classes=('DeviceClass',)
                    ),
                dict(
                     id=         'perfConfigDevice',
                     description='perfConf',
                     action=     'objRRDTemplate',
                     permissions=('Change Device',),
                     allowed_classes=('Device',)
                    ),
                dict(
                     id=         'zproperties',
                     description='zProperties',
                     action=     'zPropertyEdit',
                     permissions=('Change Device',)
                    ),
                ],
             'View':[
                dict(
                     id=         'devicelist',
                     description='Devices',
                     action=     'deviceList',
                     permissions=('View',),
                     allowed_classes=('DeviceClass',)
                    ),
                dict(
                     id=         'events',
                     description='Events',
                     action=     'viewEvents',
                     permissions=('View',)
                    ),
                dict(
                     id=         'historyEvents',
                     description='History',
                     action=     'viewHistoryEvents',
                     permissions=('View',)
                    ),
                dict(
                     id=         'classes',
                     description='Classes',
                     action=     'deviceOrganizerStatus',
                     permissions=('View',),
                     allowed_classes=('DeviceClass',)
                    ),
                dict(
                     id=         'status',
                     description='Status',
                     action=     'deviceStatus',
                     permissions=('View',),
                     allowed_classes=('Device',)
                    ),
                ],
            'Device':[
                dict(
                    id=         'moveclass',
                    description='Move to Class...',
                    action=     'dialog_moveDevices',
                    permissions=('Change Device',)
                    ),
                dict(
                    id=         'setGroups',
                    description='Set Groups...',
                    action=     'dialog_setGroups',
                    permissions=('Change Device',)
                    ),
                dict(
                    id=         'setSystems',
                    description='Set Systems...',
                    action=     'dialog_setSystems',
                    permissions=('Change Device',)
                    ),
                dict(
                    id=         'setLocation',
                    description='Set Location...',
                    action=     'dialog_setLocation',
                    permissions=('Change Device',)
                    ),
                dict(
                    id=         'removeDevices',
                    description='Delete devices...',
                    action=     'dialog_removeDevices',
                    permissions=('Change Device',)
                    ),
                dict(
                    id=         'addToZenPack',
                    description='Add to ZenPack...',
                    action=     'dialog_addToZenPack',
                    permissions=('View',)
                    ),
                ]
            })


        dmd.Networks.buildMenus(
            {'Tools':[
                dict(
                    id=             'discover',
                    description=    'Discover Devices', 
                    action=         'discoverDevices', 
                    allowed_classes='IpNetwork'
                    ),
                ]
            })
            
MenuRelations()
