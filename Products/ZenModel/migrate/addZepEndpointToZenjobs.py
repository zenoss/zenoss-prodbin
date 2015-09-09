##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
from servicemigration.endpoint import Endpoint

sm.require("1.0.0")


class AddZepEndpointToZenjobs(Migrate.Step):
    "Add zep endpoint to zenjobs services"

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Get all zenjobs services (normally only 1)
        log.info("Looking for zenjobs services to migrate")
        services = filter(lambda s: s.name == "zenjobs", ctx.services)

        # Add the zep endpoint import if it does not exist
        if not services:
            log.info("Found no 'zenjobs' services to migrate")
            # short circuit
            return
        for service in services:
            if not filter(lambda endpoint: endpoint.purpose == "import" and endpoint.application == "zep", service.endpoints):
                log.info("Adding 'zep' endpoint import to service '%s'", service.name)
                service.endpoints.append(
                    Endpoint(
                        name="zep",
                        purpose="import",
                        application="zep",
                        portnumber=8084,
                        protocol="tcp"
                    )
                )

        ctx.commit()

AddZepEndpointToZenjobs()
