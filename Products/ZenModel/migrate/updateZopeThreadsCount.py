##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import re
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class UpdateZopeThreadsCount(Migrate.Step):
    "Revert Zope threads count to default value"

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zope_services = filter(lambda s: s.name == "Zope", ctx.services)

        for zope_service in zope_services:

            # Update zope.conf.
            cf = filter(lambda f: f.name == "/opt/zenoss/etc/zope.conf", zope_service.originalConfigs)[0]

            cf.content = re.sub(
                r'^(\s*zserver-threads\s+1)\s*$',
                r'\n# Reverted to default value by ZenMigrate\n# \1\n',
                cf.content, 0, re.MULTILINE)

        # Commit our changes.
        ctx.commit()


UpdateZopeThreadsCount()
