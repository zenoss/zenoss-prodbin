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
                ('manageob','Manage','dataRootManage',('View',)),
             ],
             'View':[
                ('viewHistory','Changes','viewHistory',('View',)),
             ]
            })
        dmd.Devices.buildMenus(
            {'Edit':[
                ('manageob','Manage','deviceOrganizerManage'),
                ('editCustSchema','Custom Schema','editCustSchema',(
                    'Change Device',)),
                ('perfConfig','PerfConf','perfConfig',(
                    'Change Device',)),
                ('zproperties','zProperties','zPropertyEdit',(
                    'Change Device',)),
                ],
             'View':[
                ('devicelist','Devices','deviceList'),
                ('events','Events','viewEvents'),
                ('historyEvents','History','viewHistoryEvents'),
                ('status','Status','deviceOrganizerStatus')
                ]})


MenuRelations()
