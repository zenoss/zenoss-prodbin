#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Add usercommands to all device organizers

$Id:$
'''
import Migrate

class UserCommands(Migrate.Step):
    version = Migrate.Version(1, 0, 2)

    def cutover(self, dmd):
        for dev in dmd.Devices.getSubDevices():
            dev.buildRelations()
        for name in ['Devices', 'Systems', 'Groups', 'Locations', 'Services', 'Processes']:
            org = getattr(dmd, name)
            org.buildRelations()
            for org in org.getSubOrganizers():
                org.buildRelations()
        #for us in dmd.ZenUsers.getAllUserSettings():
        #    us.buildRelations()


UserCommands()
