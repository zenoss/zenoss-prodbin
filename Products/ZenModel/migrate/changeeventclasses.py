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
from Products.ZenEvents.EventClass import manage_addEventClass

class ChangeEventClasses(Migrate.Step):
    version = Migrate.Version(1, 0, 2)

    def cutover(self, dmd):
        if 'Change' not in [c.id for c in dmd.Events.children()]:
            manage_addEventClass(dmd.Events, 'Change')
        for name in ['Add', 'Remove', 'Set']:
            if name not in [c.id for c in dmd.Events.Change.children()]:
                manage_addEventClass(dmd.Events.Change, name)


ChangeEventClasses()
