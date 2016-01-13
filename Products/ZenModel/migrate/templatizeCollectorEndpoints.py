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
sm.require("1.0.0")


class TemplatizeCollectorEndpoints(Migrate.Step):
    "Use templated names for collector endpoints"

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):
        log.info("Migration: TemplatizeCollectorEndpoints")
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Get all zentrap and zensyslog services.
        services = filter(lambda s: s.name in ("zentrap", "zensyslog"), ctx.services)
        log.info("Found %i services named 'zentrap' or 'zensyslog'." % len(services))

        # Make sure all public Endpoints use a templated name that will prefix
        # the endpoint with the name of the parent collector
        for svc in services:
            publicEndpoints = filter(lambda endpoint: endpoint.purpose == "export", svc.endpoints)
            log.info("Found %i export endpoints for service '%s'." % (len(publicEndpoints), svc.name))
            for endpoint in publicEndpoints:
                if not endpoint.application.startswith("{{(parent .).Name}}_"):
                    log.info("Prepending parent.Name to endpoint application for '%s'." % svc.name)
                    endpoint.application = "{{(parent .).Name}}_" + endpoint.application
                else:
                    log.info("Endpoint application for '%s' already starts with parent.Name." % svc.name)

        ctx.commit()

TemplatizeCollectorEndpoints()
