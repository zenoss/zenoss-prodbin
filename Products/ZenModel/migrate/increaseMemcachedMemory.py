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
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION
log = logging.getLogger("zen.migrate")


class IncreaseMemcachedMemory(Migrate.Step):
    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        memcached_services = filter(lambda cf: cf.name == 'memcached', ctx.services)

        for service in memcached_services:
            # override ramCommitment only if it has the prior default value.
            # We don't want to change any settings the customer may have set.
            if service.ramCommitment == u'1G':
                service.ramCommitment = u'3G'

        ctx.commit()


IncreaseMemcachedMemory()
