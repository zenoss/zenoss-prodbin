##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
__doc__ = """
Disable basic auth through the GLB in for API calls
"""
import logging
import Migrate
import servicemigration as sm


log = logging.getLogger("zen.migrate")
sm.require("1.1.11")

class AddBlockAPIBasicAuth(Migrate.Step):
    version = Migrate.Version(300, 0, 3)

    def _getConfigs(self, ctx, name):
        original_conf = next(
            iter(filter(lambda s: s.name == name, ctx.originalConfigs)), None
        )
        config_file = next(
            iter(filter(lambda s: s.name == name, ctx.configFiles)), None
        )
        return (original_conf, config_file)

    def _getService(self, ctx, name):
        return next(
            iter(filter(lambda s: s.name == name, ctx.services)), None
        )

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping")
            return

        commit = False
        zproxy = ctx.getTopService()
        if not zproxy:
            log.info("Couldn't find the top level service, skipping")
            return

        if not zproxy.name == 'Zenoss.cse':
            log.info("Skipping migration in non-cse install")
            return

        log.info("Top-level service is '{}'.".format(zproxy.name))

        zproxy_configs = self._getConfigs(
            zproxy, "/opt/zenoss/zproxy/conf/zproxy-nginx.conf"
        )
        config = zproxy_configs[1]
        if config:
            # Make sure the config contains the inclusion of the disable script.
            if not "ZEN-30731:" in config.content:
                # Insert the new lines.
                content = config.content.split("\n")
                for num, line in enumerate(content):
                    if line.strip() == 'location ^~ /api/ {':
                        content[num] += '\n            # ZEN-30731: Block basic auth through the GLB\n' \
                                        '            include zproxy-disable-basic-auth.conf;'
                        break
                config.content = "\n".join(content)
                if not "ZEN-30731:" in config.content:
                    log.warn('Failed to add ZEN-30731 to zproxy-nginx.conf')
                else:
                    commit = True

        if commit:
            ctx.commit()


AddBlockAPIBasicAuth()
