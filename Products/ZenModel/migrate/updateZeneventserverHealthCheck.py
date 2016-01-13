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


class UpdateZeneventserverHealthCheck(Migrate.Step):
    "Change 'answering' healthcheck to only care about successful curl."

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):
        log.info("Migration: UpdateZeneventserverHealthCheck")
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zeps = filter(lambda s: s.name == "zeneventserver", ctx.services)
        log.info("Found %i services named 'zeneventserver'." % len(zeps))
        for zep in zeps:

            answering = filter(lambda hc: hc.name == "answering", zep.healthChecks)
            log.info("Found %i 'answering' healthchecks." % len(answering))
            for a in answering:
                a.script = "curl -f -s http://localhost:8084/zeneventserver/api/1.0/heartbeats/"
                log.info("Updated 'answering' healthcheck.")

        ctx.commit()

UpdateZeneventserverHealthCheck()
