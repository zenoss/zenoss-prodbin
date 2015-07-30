##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
In 5.0 report mail was not exposed as a run command for the zope service.
"""
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class ZopeReportMailRun(Migrate.Step):

    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # get the zope service
        zope = filter(lambda s: s.name == "Zope", ctx.services)[0]
        # set the reportmail run
        reportmailRun = filter(lambda s: s.name == "reportmail", zope.runs)
        if len(reportmailRun) == 0:
            zope.runs.append(sm.Run(
                "reportmail",
                "${ZENHOME:-/opt/zenoss}/bin/reportmail"
            ))

        # Commit our changes.
        ctx.commit()

ZopeReportMailRun()
