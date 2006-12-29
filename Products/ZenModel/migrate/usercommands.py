#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Add usercommands to all device organizers, OsProcesses, Services, etc

$Id:$
'''
import Migrate

class UserCommands(Migrate.Step):
    version = Migrate.Version(1, 1, 0)

    def cutover(self, dmd):
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
    # when walking devices also to winserv ipserv and processes
    # then when walking processes/services hit the classes but not the
    # instances of the services
                
        #for us in dmd.ZenUsers.getAllUserSettings():
        #    us.buildRelations()


UserCommands()
