###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__='''
Correctly specify DNS forward/reverse lookup  user commands for
 all device organizers, OsProcesses, Services, etc
'''
import Migrate

class correctDNSlookupCommands(Migrate.Step):
    version = Migrate.Version(2, 4, 0)

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

        # Update the DNS commands
        commands = (
                    ('DNS forward', 'host ${device/id}', "Name to IP address lookup"),
                    ('DNS reverse', 'host ${device/manageIp}', "IP address to name lookup"),
                    )
        commands = [c for c in commands
                    if c[0] in [d.id for d in dmd.userCommands()]]
        for id,cmd,desc in commands:
            command = dmd.getUserCommand(id)
            if command:
                command.manage_changeProperties(command=cmd, description=desc)

correctDNSlookupCommands()

