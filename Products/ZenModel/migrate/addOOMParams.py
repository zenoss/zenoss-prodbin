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

from Products.ZenModel.ZMigrateVersion import (
    SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION
)
from Products.ZenUtils.controlplane.client import getCCVersion

log = logging.getLogger("zen.migrate")
sm.require("1.0.0")


class AddOOMParams(Migrate.Step):
    "Add OOMKillDisable and OOMScoreAdj parameters to db services"

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        service_names = ['mariadb-model', 'redis', 'RegionServer', 'ZooKeeper',
                         'HMaster', 'Impact', 'Solr', 'mariadb-events']
        services = filter(lambda s: s.name in service_names, ctx.services)
        log.info("Found %i services" % len(services))

        cc_version = getCCVersion().split('.')
        if int(cc_version[1]) < 6 and int(cc_version[2]) < 5:
            log.info("Require CC version >= 1.6.5, skipping")
            return

        for service in services:
            if service._Service__data.get('OomKillDisable') is not None:
                service._Service__data['OomKillDisable'] = True
            if service._Service__data.get('OomScoreAdj') is not None:
                service._Service__data['OomScoreAdj'] = 0
        ctx.commit()

AddOOMParams()
