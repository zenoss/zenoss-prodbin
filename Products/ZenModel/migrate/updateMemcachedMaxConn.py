#############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import re
import Migrate
from Products.ZenModel.ZMigrateVersion import (
SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION
)
import servicemigration as sm
sm.require("1.1.11")

class updateMemcachedMaxConn(Migrate.Step):
    """
    Update memcached service def to change default MaxConn value from 1024 to 4096
    """

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def _update_config(self, config):

        config = re.sub(r'1024', r'4096', config)
        return config

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        memcached_services = filter(lambda cf: cf.name == 'memcached', ctx.services)

        for service in memcached_services:
            cfs = filter(lambda cf: cf.name == "/etc/sysconfig/memcached",
                         service.originalConfigs + service.configFiles)
            for cf in cfs:
                cf.content = self._update_config(cf.content)

        ctx.commit()

updateMemcachedMaxConn()
