##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import Migrate
import servicemigration as sm
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION

log = logging.getLogger("zen.migrate")
sm.require("1.1.14")


class AddPIDFiles(Migrate.Step):
    "Add PIDFiles to services"

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        pidFiles = {
            "Impact": "exec echo /opt/zenoss_impact/var/zenoss_impact.pid",
        }

        services = filter(lambda s: s.name in pidFiles.keys(), ctx.services)
        for service in services:
            service.pidFile = pidFiles[service.name]
        ctx.commit()

AddPIDFiles()
