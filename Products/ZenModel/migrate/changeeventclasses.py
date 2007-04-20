###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__='''

Add usercommands to all device organizers, OsProcesses, Services, etc

$Id:$
'''
import Migrate
from Products.ZenEvents.EventClass import manage_addEventClass

class ChangeEventClasses(Migrate.Step):
    version = Migrate.Version(1, 1, 0)

    def cutover(self, dmd):
        if 'Change' not in [c.id for c in dmd.Events.children()]:
            manage_addEventClass(dmd.Events, 'Change')
        dmd.Events.Change.zEventAction = 'history'
        for name in ['Add', 'Remove', 'Set']:
            if name not in [c.id for c in dmd.Events.Change.children()]:
                manage_addEventClass(dmd.Events.Change, name)


ChangeEventClasses()
