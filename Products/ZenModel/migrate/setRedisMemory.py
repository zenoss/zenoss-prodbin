#############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import re
import Migrate
import servicemigration as sm
sm.require("1.1.11")

CURRENT_MEMORY_PATTERN = re.compile('maxmemory[ ]*1gb')
NEW_MEMORY = 'maxmemory {{percentScale .RAMCommitment 0.9}}'

class setRedisMemory(Migrate.Step):
    """
    Update Infrastrcuture/Redis config file to change maxmemory to 90% of RAMCommitment
    """

    version = Migrate.Version(300, 0, 8)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        redis_services = filter(lambda cf: cf.name == 'redis', ctx.services)
        for service in redis_services:
            # Update config file - don't care about orignalConfigs
            cfs = filter(lambda cf: cf.name == "/etc/redis.conf", service.configFiles)
            for cf in cfs:
               log.info("Updating redis maxmemory to be based on RAMCommitment in config file %s for %s service", cf.name, service.name)
               cf.content = CURRENT_MEMORY_PATTERN.sub(NEW_MEMORY,cf.content)

        ctx.commit()

setRedisMemory()
