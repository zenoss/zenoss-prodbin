##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
Switch default logging level to INFO
"""
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import yaml
import servicemigration as sm
sm.require("1.0.0")


class SwitchLoggingLevel(Migrate.Step):

    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        cqs = filter(lambda s: s.name == 'CentralQuery', ctx.services)
        if len(cqs) != 1:
            log.info("Found %i services named 'CentralQuery'; skipping.", len(cqs))
            return

        cqconfigs = filter(lambda cf: cf.name == '/opt/zenoss/etc/central-query/configuration.yaml', cqs[0].originalConfigs)
        log.info("Found %i configs named '/opt/zenoss/etc/central-query/configuration.yaml'." % len(cqconfigs))
        for cqconfig in cqconfigs:
            confyaml = yaml.load(cqconfig.content)

            old_level = confyaml['logging']['level']
            log.info("Updating log level to 'INFO' (was '%s')." % old_level)
            confyaml['logging']['level'] = 'INFO'

            old_oz = confyaml['logging']['loggers']['org.zenoss']
            confyaml['logging']['loggers']['org.zenoss'] = 'INFO'
            log.info("Updating zenoss log level to 'INFO' (was '%s')." % old_oz)

            cqconfig.content = yaml.dump(confyaml)

        ctx.commit()

SwitchLoggingLevel()
