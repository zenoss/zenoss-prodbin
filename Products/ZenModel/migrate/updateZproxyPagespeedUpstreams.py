##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import re

log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class UpdateZproxyPagespeedUpstreams(Migrate.Step):

    version = Migrate.Version(5,2,0)

    config_file = "/opt/zenoss/zproxy/conf/zproxy-nginx.conf"
    save_file = "/opt/zenoss/var/ext/zproxy-nginx.conf.orig"

    def update_zope_imports(self, zproxy):
        for endpoint in service.endpoints:
            if endpoint.application == "zope":
                if endpoint.purpose == "import":
                    endpoint.purpose == "import_all"
                    return True
                return False

    def update_config(self, zproxy):
        commit, wrote = False, False
        current_config, orig_config = None, None

        with open(self.config_file) as new_file:
            new_content = new_file.read()

        for cfg in zproxy.configFiles:
            if cfg.filename == self.config_file:
                current_config = cfg
                break

        for cfg in zproxy.originalConfigs:
            if cfg.filename == self.config_file:
                orig_config = cfg
                break

        if orig_config and orig_config.content != new_content:
            orig_config.write(new_content)
            commit = True

        if current_config and current_config.content != new_content:
            with open(self.save_file, 'w+') as f:
                f.write(current_config.content)
            current_config.content = new_content
            commit = True
            wrote = True

        return commit, wrote


    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zproxy = ctx.getTopService()

        commit, wrote = self.update_config(zproxy)
        commit = commit or self.update_zope_imports(zproxy)

        try:
            if commit:
                log.info("Updated zproxy configuration to the latest version.")
                ctx.commit()
        finally:
            if wrote:
                log.info(("A copy of your existing configuration has been saved to {save_file}."
                        " If you had made changes to zproxy-nginx.conf in the Control Center UI, "
                        "please reapply them manually, then restart the service.") % self.save_file)


UpdateZproxyPagespeedUpstreams()
