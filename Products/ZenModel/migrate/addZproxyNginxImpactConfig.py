##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """Add proper pagespeed filter for impact
"""

import logging
import re
log = logging.getLogger("zen.migrate")

from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION
import Migrate
import servicemigration as sm
sm.require("1.1.5")

org_statement='pagespeed Disallow \"*/static/*\";\n\n'
new_statement='pagespeed  Disallow \"*/static/*\";\n        pagespeed  Disallow \"*/impact_graph*\";\n        pagespeed  Allow    \"*/impact_graph*.js\";\n\n'

class AddZproxyNginxImpactConfig(Migrate.Step):
    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    config_file = "/opt/zenoss/zproxy/conf/zproxy-nginx.conf"
    save_file = "/opt/zenoss/var/ext/zproxy-nginx.conf.orig"

    def update_config(self, zproxy):
        commit, wrote = False, False
        current_config, orig_config = None, None

        for cfg in zproxy.configFiles:
            if cfg.filename == self.config_file:
                current_config = cfg
                break

        for cfg in zproxy.originalConfigs:
            if cfg.filename == self.config_file:
                orig_config = cfg
                break

        if orig_config:
            new_content = orig_config.content.replace(org_statement, new_statement)
            if orig_config.content != new_content:
                orig_config.content = new_content
                commit = True

        if current_config:
            new_content = current_config.content.replace(org_statement, new_statement)
            if current_config.content != new_content:
                with open(self.save_file, 'w+') as f:
                    f.write(current_config.content)
                wrote = True
                current_config.content = new_content
                commit = True

        return commit, wrote

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zproxy = ctx.getTopService()

        commit, wrote = self.update_config(zproxy)

        try:
            if commit:
                log.info("Updated zproxy configuration to the latest version.")
                ctx.commit()
        finally:
            if wrote:
                log.info(("A copy of your existing configuration has been saved to %s which is mounted to host's /opt/serviced/var/volumes/.../zenoss-var-ext directory.") % self.save_file)


AddZproxyNginxImpactConfig()
