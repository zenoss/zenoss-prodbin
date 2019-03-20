import logging
import itertools
import Migrate
import servicemigration as sm

from servicemigration.endpoint import Endpoint


log = logging.getLogger("zen.migrate")
sm.require("1.1.11")


class AddZingEndpointsToZenhubworker(Migrate.Step):

    version = Migrate.Version(300, 0, 7)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return


        new_endpoints = [
            Endpoint(
                name="zing-connector",
                purpose="import",
                application="zing-connector",
                applicationtemplate="zing-connector",
                portnumber=9237,
                protocol="tcp"
            ),
            Endpoint(
                name="zing-connector-admin",
                purpose="import",
                application="zing-connector-admin",
                applicationtemplate="zing-connector-admin",
                portnumber=9000,
                protocol="tcp"
            )
        ]


        log.info("Looking for zenhubworkers services to migrate")
        services = filter(lambda s: s.name == "zenhubworker", ctx.services)

        if not services:
            log.info("No 'zenhubworker' services found to migrate")
            return

        changed = False
        for service, new_endpoint in itertools.product(services, new_endpoints):
            if not filter(lambda endpoint: endpoint.purpose == new_endpoint.purpose and endpoint.application == new_endpoint.application, service.endpoints):
                log.info("Adding '%s' endpoint import to service '%s'", new_endpoint.name, service.name)
                service.endpoints.append(new_endpoint)
                changed = True

        if changed:
            ctx.commit()

AddZingEndpointsToZenhubworker()
