##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
__doc__ = """
Disable basic auth through the GLB in CSE
"""
import logging
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION
import Migrate
import servicemigration as sm

log = logging.getLogger("zen.migrate")

sm.require("1.1.11")

_ConfigContent = """\
# ZEN-30567: disallow basic auth on the glb
set $auth_flags "";
if ($http_via ~ 'google') {
    set $auth_flags "${auth_flags}1";
}
if ($http_authorization ~ '(?i)^basic') {
    set $auth_flags "${auth_flags}1";
}
if ($auth_flags = 11) {
    return 403;
}
"""

class AddBlockBasicAuth(Migrate.Step):
    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

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

        original, config = self._getConfigs(
            zproxy, "/opt/zenoss/zproxy/conf/zproxy-disable-basic-auth.conf"
        )

        log.info("Top-level service is '{}'.".format(zproxy.name))

        new_config = sm.ConfigFile(
            name="/opt/zenoss/zproxy/conf/zproxy-disable-basic-auth.conf",
            filename="/opt/zenoss/zproxy/conf/zproxy-disable-basic-auth.conf",
            owner="zenoss:zenoss",
            permissions="644",
            content=_ConfigContent
        )

        if not config:
            zproxy.configFiles.append(new_config)
            log.info("Added %s config to service %s configFiles", new_config.name, zproxy.name)
            commit = True

        if not original:
            zproxy.originalConfigs.append(new_config)
            log.info("Added %s config to service %s originalConfigs", new_config.name, zproxy.name)
            commit = True

        zproxy_configs = self._getConfigs(
            zproxy, "/opt/zenoss/zproxy/conf/zproxy-nginx.conf"
        )
        config = zproxy_configs[1]
        if config:
            # Make sure the config contains the inclusion of the disable script.
            if not "ZEN-30567:" in config.content:
                # Insert the new lines.
                content = config.content.split("\n")
                location = False
                for num, line in enumerate(content):
                    if line.strip() == 'location / {':
                        location = True
                        content[num] += '\n            # ZEN-30567: disallow basic auth on the glb\n'\
                                        '            include zproxy-disable-basic-auth.conf;\n'
                    elif location and line.strip() == '}':
                        content[num] += '\n\n        location ~* ^/zport/acl_users/cookieAuthHelper/login {\n'\
                                        '            # ZEN-30567: Disallow the basic auth login page.\n'\
                                        '            return 403;\n        }'
                    elif line.strip() == 'location ~* ^/zport/dmd/reports {':
                        content[num] += '\n            # ZEN-30567: disallow basic auth on the glb\n'\
                                        '            include zproxy-disable-basic-auth.conf;\n'
                        break
                config.content = "\n".join(content)
                commit = True

        if commit:
            ctx.commit()


AddBlockBasicAuth()
