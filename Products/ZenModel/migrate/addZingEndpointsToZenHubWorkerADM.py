##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import itertools
import Migrate
import servicemigration as sm

from servicemigration.endpoint import Endpoint

log = logging.getLogger("zen.migrate")
sm.require("1.1.11")

ZING_ENDPOINTS = (
    Endpoint(
        name="zing-connector",
        purpose="import",
        application="zing-connector",
        applicationtemplate="zing-connector",
        portnumber=9237,
        protocol="tcp",
    ),
    Endpoint(
        name="zing-connector-admin",
        purpose="import",
        application="zing-connector-admin",
        applicationtemplate="zing-connector-admin",
        portnumber=9000,
        protocol="tcp",
    ),
)


class AddZingEndpointsToZenhubWorkerADM(Migrate.Step):
    """Add Zing endpoints to the "zenhubworker (adm)" service."""

    version = Migrate.Version(300, 0, 11)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        log.info("Looking for zenhubworkers services to migrate")
        services = [s for s in ctx.services if s.name == "zenhubworker (adm)"]

        if not services:
            log.info("No 'zenhubworker (adm)' services found to migrate")
            return

        changed = False
        for service, zing_endpoint in itertools.product(
            services, ZING_ENDPOINTS,
        ):
            if not filter(
                lambda endpoint: endpoint.purpose == zing_endpoint.purpose
                and endpoint.application == zing_endpoint.application,
                service.endpoints,
            ):
                log.info(
                    "Adding '%s' endpoint import to service '%s'",
                    zing_endpoint.name, service.name,
                )
                service.endpoints.append(zing_endpoint)
                changed = True
            else:
                log.info(
                    "Service '%s' already has endpoint '%s'.",
                    service.name, zing_endpoint.name,
                )

        if changed:
            ctx.commit()


AddZingEndpointsToZenhubWorkerADM()
