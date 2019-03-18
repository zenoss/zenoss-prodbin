##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
__doc__ = """
Add pendo URL mapping to zproxy-nginx.conf
"""
import logging
import re

log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm

from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION

sm.require("1.1.12")

class EnableNginxPendo(Migrate.Step):
    '''
    Add URL mapping for pendo to zproxy-nginx.conf
    '''

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping")
            return

        commit = False
        zproxy = ctx.getTopService()
        log.info("Top-level service is '{}'.".format(zproxy.name))
        configfiles = zproxy.originalConfigs + zproxy.configFiles
        for config_file in filter(lambda f: f.name == '/opt/zenoss/zproxy/conf/zproxy-nginx.conf', configfiles):
            config_text = config_file.content

            pendo_setting = re.search("pendostatic", config_text)
            if pendo_setting is not None:
                continue

            newContent = []
            inRootLocation = False
            lines = config_text.split('\n')
            for line in lines:
                newContent.append(line)
                stripped = line.strip()

                if stripped.startswith("location / {"):
                    inRootLocation = True
                    continue
                elif inRootLocation and stripped.startswith("}"):
                    inRootLocation = False
                elif inRootLocation and stripped.startswith("sub_filter \"/static/\""):
                    newContent.append("            # ZEN-31143 - The \"/pendostatic/\" is an artificial path element used to avoid conflicts")
                    newContent.append("            # between Pendo's \"/static/\" and RM's \"/static/\", so we have to replace it with the")
                    newContent.append("            # real path Pendo expects (i.e. \"/agent/static/...\").")
                    newContent.append("            sub_filter \"/agent/pendostatic/\" \"/agent/static/\";")

            if len(newContent) != len(lines):
                # we added something
                log.info("Turn on pendo URL mapping for {} and {}".format(config_file.name, zproxy.name))
                commit = True;
                config_file.content = '\n'.join(newContent)

        if commit:
            ctx.commit()

EnableNginxPendo()
