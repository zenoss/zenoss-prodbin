##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
Switch default logging level to WARN
"""
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import yaml
import servicemigration as sm
sm.require("1.0.0")


class SwitchLoggingLevel(Migrate.Step):

    version = Migrate.Version(5, 0, 8)

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

        commit = False
        cqconfigs = filter(lambda cf: cf.name == '/opt/zenoss/etc/central-query/configuration.yaml', cqs[0].originalConfigs)
        if cqconfigs:
            for cqconfig in cqconfigs:
                confyaml = yaml.load(cqconfig.content)
                level, loggers = (confyaml['logging']['level'],
                                  confyaml['logging']['loggers']['org.zenoss'])
                if (level, loggers) != ('WARN', 'WARN'):
                    confyaml['logging']['level'] = 'WARN'
                    confyaml['logging']['loggers']['org.zenoss'] = 'WARN'
                    cqconfig.content = yaml.dump(confyaml)
                    commit = True

        if commit:
            ctx.commit()

SwitchLoggingLevel()
