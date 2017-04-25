##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import Migrate
import os
import servicemigration as sm

log = logging.getLogger("zen.migrate")
sm.require("1.0.0")

#
# Fixes redis configs to allow remote connections after the introduction of
# protected-mode in newer versions.
#
class UpdateRedisBindAddress(Migrate.Step):
    version = Migrate.Version(111, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        redises = filter(lambda s: "redis" in s.name, ctx.services)
        log.info("Found {0} services with 'redis' in their service path".format(len(redises)))
        for redis in redises:
            log.info("{0}".format(redis))
            cfs = filter(lambda f: f.name == "/etc/redis.conf", redis.originalConfigs + redis.configFiles)
            for cf in cfs:
                lines = cf.content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith("#bind " or line.startswith("bind ")):
                        lines[i] = "bind 0.0.0.0"
                        log.info("Changed Redis bind setting to 0.0.0.0")
                cf.content = '\n'.join(lines)
        # Commit our changes.
        ctx.commit()

UpdateRedisBindAddress()
