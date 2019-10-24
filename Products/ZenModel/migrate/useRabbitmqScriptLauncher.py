##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging
import servicemigration as sm

from itertools import chain
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION

from . import Migrate

log = logging.getLogger("zen.migrate")
sm.require("1.1.11")


class UseRabbitmqScriptLauncher(Migrate.Step):
    """Modify rabbit_supervisor.conf to use new launcher script."""

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        service = next(
            (s for s in ctx.services if s.name == "RabbitMQ"), None,
        )
        if service is None:
            log.error("Unable to find 'RabbitMQ' service")
            return

        config_files = chain(service.configFiles, service.originalConfigs)
        config_name = "/etc/rabbitmq/rabbit_supervisor.conf"
        supervisor_configs = [
            cf for cf in config_files if cf.name == config_name
        ]
        pattern = "command=/usr/sbin/rabbitmq-server"
        replacement = "command=/opt/zenoss/bin/rabbitmq.sh"
        for config in supervisor_configs:
            config.content = config.content.replace(pattern, replacement)

        if len(supervisor_configs):
            ctx.commit()
            log.info("Updated '%s' config file", config_name)
        else:
            log.error("Unable to find config file '%s'", config_name)


UseRabbitmqScriptLauncher()
