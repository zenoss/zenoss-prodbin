##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import Migrate
import servicemigration as sm

log = logging.getLogger("zen.migrate")
sm.require("1.0.0")


class AddMariaDBEnvVariables(Migrate.Step):
    version = Migrate.Version(300, 0, 13)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zodb_env_entry = "MARIADB_DB=zodb"
        zep_env_entry = "MARIADB_DB=zep"

        mariadbservices = filter(lambda s: "mariadb" in s.name, ctx.services)
        log.info("Found {0} services with 'mariadb' in their service path".format(len(mariadbservices)))

        commit = False
        for mariaDBservice in mariadbservices:
            if mariaDBservice.name == 'mariadb-model' and zodb_env_entry not in mariaDBservice.environment:
                mariaDBservice.environment.append(zodb_env_entry)
                commit = True
                log.info("Added env variable for %s service", mariaDBservice.name)
            if mariaDBservice.name == 'mariadb-events' and zep_env_entry not in mariaDBservice.environment:
                mariaDBservice.environment.append(zep_env_entry)
                commit = True
                log.info("Added env variable for %s service", mariaDBservice.name)

        if commit:
            ctx.commit()


AddMariaDBEnvVariables()

