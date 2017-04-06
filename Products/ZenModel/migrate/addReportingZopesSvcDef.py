##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
import servicemigration.thresholdconfig
import servicemigration.threshold
import servicemigration.eventtags

import re

sm.require("1.1.6")

class addReportingZopesSvcDef(Migrate.Step):
    """Adds a threshold for missedRuns for collector services"""

    version = Migrate.Version(111,0,0)

    def add_zenreports_svc(self, ctx):
        # zenreports is a clone of Zope dedicated to generating resmgr reports
        zopesvc = filter(lambda x: x.name == "Zope" and x.description == "Zope server", ctx.services)[0]
        zenreports_svc = zopesvc.clone()

        # Change the name
        zenreports_svc.name = "zenreports"
        # Change the description
        zenreports_svc.description = "Zope server dedicated to report generation"
        # Change the StartupCommand
        zenreports_svc.startup = "su - zenoss -c \"CONFIG_FILE=${ZENHOME:-/opt/zenoss}/etc/zenreports.conf /opt/zenoss/bin/runzope\" "
        # Remove the Commands
        zenreports_svc.commands = []
        # Change the ConfigFiles
        zopeconf = filter(lambda x: x.name == "/opt/zenoss/etc/zope.conf", zenreports_svc.originalConfigs)[0]
        zenreports_svc.originalConfigs = filter(lambda x: x.name != "/opt/zenoss/etc/zope.conf",zenreports_svc.originalConfigs)
        zenreports_svc.originalConfigs.append(sm.ConfigFile(
                        name = "/opt/zenoss/etc/zenreports.conf",
                        filename = "/opt/zenoss/etc/zenreports.conf",
                        owner = "zenoss:zenoss",
                        permissions = "660",
                        content = zopeconf.content.replace('9080', '9290')
                    ))
        zenreports_svc.configFiles = filter(lambda x: x.name != "/opt/zenoss/etc/zope.conf",zenreports_svc.configFiles)
        zenreports_svc.configFiles.append(sm.ConfigFile(
                        name = "/opt/zenoss/etc/zenreports.conf",
                        filename = "/opt/zenoss/etc/zenreports.conf",
                        owner = "zenoss:zenoss",
                        permissions = "660",
                        content = zopeconf.content.replace('9080', '9290')
                    ))
        # Remove the zope Endpoints entry, add one for zenreports
        zenreports_svc.endpoints = filter(lambda x: x.name != "zope", svc.endpoints)
        zenreports_svc.endpoints.append(sm.Endpoint(
            name = "zenreports",
            application = "zenreports",
            portnumber = 9290,
            protocol = "tcp",
            purpose = "export"
        ))
        # Change the answering.script entry in HealthChecks
        answering = filter(lambda x: x.name == "answering", zenreports_svc)[0]
        answering.script = answering.script.replace('9080', '9290')
        # Change Instances.default and Instances.min
        zenreports_svc.instanceLimits.minimum = 0
        zenreports_svc.instanceLimits.default = 1

        # Add the zenreports service
        ctx.services.append(zenreports_svc)
        return True

    def _insert_zenreport_nginx_incls(self, zprox_conf):
        # Insert zenreports upstreams server decl
        zopereports_upstreams_decl = "\n\n    upstream zopereports {\n        least_conn;\n        include zopereports-upstreams.conf;\n        keepalive 64;\n    }"
        mimetypes_match = re.search(r"include mime.types;\r\n", zproxy_conf.content)
        if mimetypes_match:
            upstreams_insertion_point = mimetypes_match.end()
            new_zproxy_conf_content = zproxy_conf.content[0:upstreams_insertion_point] + zopereports_upstreams_decl + zproxy_conf.content[upstreams_insertion_point:]
            zproxy_conf.content = new_zproxy_conf_content
        else:
            return False

        # Insert zopereports-proxy.conf include after root location decl
        root_location_decl_regex = r"location\s+/\s+{[\\\w\s\-\.;\$]+}(\\[rn])+"
        root_location_decl_match = re.search(root_location_decl_regex, zproxy_conf.content)
        zopereports_proxy_incl = "        include zopereports-proxy.conf;\n\n"
        if root_location_decl_match:
            zopereports_proxy_insertion_point = root_location_decl_match.end()
            new_zproxy_conf_content = zproxy_conf.content[0:zopereports_proxy_insertion_point] + zopereports_proxy_incl + zproxy_conf.content[zopereports_proxy_insertion_point:]
            zproxy_conf.content = new_zproxy_conf_content
        else:
            return False

    def update_zproxy_configs(self, zproxy):
        #Add endpoint for new zenreports service
        zproxy.endpoints.append(sm.Endpoint(
            name = "zenreports",
            application = "zenreports",
            portnumber = 9290,
            protocol = "tcp",
            purpose = "import_all"
        ))
        # Add configs for zopereports upstream and proxy included zproxy-nginx.conf
        zproxy.originalConfigs.append(sm.ConfigFile(
            name = "/opt/zenoss/zproxy/conf/zopereports-proxy.conf",
            filename = "/opt/zenoss/zproxy/conf/zopereports-proxy.conf",
            owner = "zenoss:zenoss",
            permissions = "644",
            content = "        location ~* ^/zport/dmd/reports {\n            proxy_pass http://zopereports;\n            proxy_set_header Host $myhost;\n            proxy_http_version 1.1;\n            add_header X-Frame-Options SAMEORIGIN;\n            add_header X-XSS-Protection \"1; mode=blocki\";\n        }"
        ))

        zproxy.originalConfigs.append(sm.ConfigFile(
            name = "/opt/zenoss/zproxy/conf/zopereports-upstreams.conf",
            filename = "/opt/zenoss/zproxy/conf/zopereports-upstreams.conf",
            owner = "zenoss:zenoss",
            permissions = "644",
            content = "server 127.0.0.1:9290;"
        ))

        #Modify zproxy configs for zenreports
        zproxy_conf_orig = filter(lambda x: x.name == "/opt/zenoss/zproxy/conf/zproxy-nginx.conf", zproxy.originalConfigs)
        zproxy_conf = filter(lambda x: x.name == "/opt/zenoss/zproxy/conf/zproxy-nginx.conf", zproxy.configFiles)
        return self._insert_zenreport_nginx_incls(zprox_conf_orig) and self._insert_zenreport_nginx_incls(zprox_conf)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate context, skipping.")
            return

        did_add_zenreports = self.add_zenreports_svc(ctx)

        zproxy = ctx.getTopService()
        did_update_zproxy_configs = update_zproxy_configs(zproxy)

        # Commit our changes
        if did_add_zenreports and did_update_zproxy_configs:
            ctx.commit()

addReportingZopesSvcDef()
