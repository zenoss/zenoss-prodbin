##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = '''
Increase memcached RAMComminment
'''

import logging
import Migrate
import re
import servicemigration as sm
log = logging.getLogger("zen.migrate")


class IncreaseMemcachedMemory(Migrate.Step):
    version = Migrate.Version(200, 2, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        memcached_services = filter(lambda cf: cf.name == 'memcached', ctx.services)

        for service in memcached_services:
            service.ramCommitment = u'3G'

        ctx.commit()


IncreaseMemcachedMemory()
