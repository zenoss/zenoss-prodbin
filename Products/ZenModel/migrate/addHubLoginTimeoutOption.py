##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION

sm.require("1.0.0")

class AddHubLoginTimeoutOption(Migrate.Step):
    """Add ZenHub login timeout option."""

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        loginTimeoutOption = [
            '# ZenHub login timeout option',
            '#  default: 60',
            '#hubLoginTimeout 60',
            '#']

        servicesToUpdate = set()
        servicedefAlreadyUpdated = set()

        commit = False

        for service in ctx.services:
            configs = service.originalConfigs + service.configFiles
            for config in configs:
                if 'hubLoginTimeout' in config.content:
                    servicedefAlreadyUpdated.add(service)
                    commit = False
                    continue
                if 'initialHub' in config.content:
                    servicesToUpdate.add(service)
                    config_list = config.content.split('\n')
                    for item in config_list:
                        if '#initialHubTimeout' in item:
                            found = config_list.index(item)
                            config_list[found + 2:found + 2] = loginTimeoutOption
                            config.content = '\n'.join(config_list)
                            commit = True

        if commit:
            log.info("Updating %d services" % len(servicesToUpdate))
            ctx.commit()
        else:
            log.warn("Services already updated: %d" % len(servicedefAlreadyUpdated))

AddHubLoginTimeoutOption()
