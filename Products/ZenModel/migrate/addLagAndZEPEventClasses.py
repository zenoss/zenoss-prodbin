##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Migrate
from Products.ZenEvents.EventClass import manage_addEventClass

from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION


class AddLagAndZEPEventClasses(Migrate.Step):
    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):
        if 'Lag' not in [i.id for i in dmd.Events.Status.Ping.getSubEventClasses()]:
            manage_addEventClass(dmd.Events.Status.Ping, 'Lag')
        if 'ZEP' not in [i.id for i in dmd.Events.Status.getSubEventClasses()]:
            manage_addEventClass(dmd.Events.Status, 'ZEP')


AddLagAndZEPEventClasses()
