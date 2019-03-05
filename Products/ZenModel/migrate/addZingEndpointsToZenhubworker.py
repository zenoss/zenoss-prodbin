import logging
import itertools
import Migrate
import servicemigration as sm

from servicemigration.endpoint import Endpoint
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION


log = logging.getLogger("zen.migrate")
sm.require("1.1.11")


class AddZingEndpointsToZenhubworker(Migrate.Step):

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return


        endpoint_map = {
            'zing-connector': Endpoint(
                name="zing-connector",
                purpose="import",
                application="zing-connector",
                portnumber=9237,
                protocol="tcp"
            ),
            'zing-connector-admin': Endpoint(
                name="zing-connector-admin",
                purpose="import",
                application="zing-connector-admin",
                portnumber=9000,
                protocol="tcp"
            )
        }


        log.info("Looking for zenhubworkers services to migrate")
        services = filter(lambda s: s.name == "zenhubworker", ctx.services)

        if not services:
            log.info("No 'zenhubworker' services found to migrate")
            return

        for service, endpoint_key in itertools.product(services, endpoint_map.keys()):
            if not filter(lambda endpoint: endpoint.purpose == "import" and endpoint.application == endpoint_key, service.endpoints):
                log.info("Adding '%s' endpoint import to service '%s'", endpoint_key, service.name)
                service.endpoints.append(
                    endpoint_map[endpoint_key]
                )

        ctx.commit()

AddZingEndpointsToZenhubworker()
