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


class AddKibanaRouteInZproxyConf(Migrate.Step):

    version = Migrate.Version(5,1,9)

    KIBANA_NEW_ROUTE_CONFIG = """

        location ^~ /api/controlplane/kibana {
            set $http_ws true;
            proxy_pass http://127.0.0.1:5601;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            rewrite /api/controlplane/kibana$ / break;
            rewrite /api/controlplane/kibana/(.*)$ /$1 break;
        }"""

    CONFIG_FILENAME = "/opt/zenoss/zproxy/conf/zproxy-nginx.conf"

    OLD_ROUTE_RE="(location\s*\^\~\s*\/logview\/)"
    NEW_ROUTE_RE="(location\s*\^\~\s*\/api\/controlplane\/kibana)"

    def _update_kibana_config(self, zproxy_config, old_route_string):
        """
        Find the old kibana route and replace it with the new one
        @param old_route_string: old route string found in the config file
        """
        new_content = ""
        start = zproxy_config.content.find(old_route_string)
        end = zproxy_config.content.find("}", start)
        new_content = zproxy_config.content[:end+1] + \
                      self.KIBANA_NEW_ROUTE_CONFIG + \
                      zproxy_config.content[end+1:]
        zproxy_config.content = new_content

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zproxy = ctx.getTopService()
        commit = False
        for configs in [zproxy.configFiles, zproxy.originalConfigs]:
            for config in configs:
                if config.filename == self.CONFIG_FILENAME:
                    old_match = re.search(self.OLD_ROUTE_RE, config.content)
                    new_match = re.search(self.NEW_ROUTE_RE, config.content)
                    if old_match and not new_match:
                        old_route_string = old_match.groups()[0]
                        self._update_kibana_config(config, old_route_string)
                        commit = True
        if commit:
            log.info("Kibana configuration updated in {0}.".format(self.CONFIG_FILENAME))
            ctx.commit()


AddKibanaRouteInZproxyConf()



