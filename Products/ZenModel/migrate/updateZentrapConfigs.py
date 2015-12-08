##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class UpdateZentrapConfigs(Migrate.Step):
    "Add zentrap.filter.conf and alter zentrap.conf."

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zentraps = filter(lambda s: s.name == "zentrap", ctx.services)

        cfFilter = sm.ConfigFile (
            name = "/opt/zenoss/etc/zentrap.filter.conf",
            filename = "/opt/zenoss/etc/zentrap.filter.conf",
            owner = "zenoss:zenoss",
            permissions = "0664",
            content = open(os.path.join(os.path.dirname(__file__), "config-files", "zentrap.filter.conf"), 'r').read()
        )

        commit = False
        new_config = open(os.path.join(os.path.dirname(__file__), "config-files", "zentrap.conf"), 'r').read()
        for zentrap in zentraps:

            # First update zentrap.conf.
            zentrap_confs = filter(lambda f: f.name == "/opt/zenoss/etc/zentrap.conf", zentrap.originalConfigs)
            for config in zentrap_confs:
                if config.content != new_config:
                    config.content = new_config
                    commit = True

            # Now add zentrap.filter.conf.
            zentrap_filter_confs = filter(lambda f: f.name == "/opt/zenoss/etc/zentrap.filter.conf", zentrap.originalConfigs)
            if not zentrap_filter_confs:
                zentrap.originalConfigs.append(cfFilter)
                commit = True

        # Commit our changes.
        if commit:
            ctx.commit()


UpdateZentrapConfigs()
