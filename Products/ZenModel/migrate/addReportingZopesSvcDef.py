##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """AddReportingZopesSvcDef
Adds service zenreports that provides Zope instances dedicated to generating
resmgr reports.
"""
import logging
log = logging.getLogger("zen.migrate")

import os
import re
import copy
import Migrate
import servicemigration as sm
import servicemigration.thresholdconfig
import servicemigration.threshold
import servicemigration.eventtags


sm.require("1.1.8")

class AddReportingZopesSvcDef(Migrate.Step):
    """Adds a svcdef for dedicated reporting Zope"""
    version = Migrate.Version(112,0,0)

    def __init__(self):
        Migrate.Step.__init__(self)
        self.zenreports_upstreams_decl = "\n    upstream zopereports {\n        least_conn;\n        include zopereports-upstreams.conf;\n        keepalive 64;\n    }\n"
        self.zenreports_proxy_incl = "\n        include zopereports-proxy.conf;\n\n"

    def _add_zenreports_service(self, ctx):
        zenreports_svc = filter(lambda x: x.name == "zenreports", ctx.services)
        if zenreports_svc and len(zenreports_svc) > 0:
            zenreports_svc = zenreports_svc[0]
            log.info("The zenreports service already exists. Skipping this migration step.")
            return False

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
        zenreports_conf = sm.ConfigFile(
                        name = "/opt/zenoss/etc/zenreports.conf",
                        filename = "/opt/zenoss/etc/zenreports.conf",
                        owner = "zenoss:zenoss",
                        permissions = "660",
                        content = zopeconf.content.replace('9080', '9290')
                    )
        zenreports_svc.originalConfigs = filter(lambda x: x.name != "/opt/zenoss/etc/zope.conf",zenreports_svc.originalConfigs)
        zenreports_svc.originalConfigs.append(zenreports_conf)
        zenreports_svc.configFiles = filter(lambda x: x.name != "/opt/zenoss/etc/zope.conf",zenreports_svc.configFiles)
        zenreports_svc.configFiles.append(zenreports_conf)
        # Remove the zope Endpoints entry, add one for zenreports
        zenreports_svc.endpoints = filter(lambda x: x.name != "zope", zenreports_svc.endpoints)
        zenreports_svc.endpoints.append(sm.Endpoint(
            name = "zenreports",
            application = "zenreports",
            portnumber = 9290,
            protocol = "tcp",
            purpose = "export"
        ))
        # Change the answering.script entry in HealthChecks
        answering = filter(lambda x: x.name == "answering", zenreports_svc.healthChecks)[0]
        answering.script = answering.script.replace('9080', '9290').replace('Zope', 'zenreports')
        # Change Instances.default and Instances.min
        zenreports_svc.instanceLimits.minimum = 1
        zenreports_svc.instanceLimits.default = 1
        zenreports_svc.instances = 1

        # Add the zenreports service
        ctx.services.append(zenreports_svc)

        return True

    def insertUpstreamDecl(self, matchObj):
        return "{}{}".format(matchObj.group(0), self.zenreports_upstreams_decl)

    def insertProxyDecl(self, matchObj):
        return "{}{}".format(self.zenreports_proxy_incl, matchObj.group(0))

    def _insert_zenreport_nginx_incls(self, zproxy_conf):
        # Insert zenreports upstreams server decl
        if re.search("upstream zopereports", zproxy_conf.content) is not None:
            return False
        if re.search("include zopereports-proxy.conf", zproxy_conf.content) is not None:
            return False
        zproxy_conf_a = re.sub(r'(include mime.types;(?:\r\n|\s+))', self.insertUpstreamDecl, zproxy_conf.content)
        zproxy_conf_b = re.sub('        location / {', self.insertProxyDecl, zproxy_conf_a)
        zproxy_conf.content = zproxy_conf_b
        return True

    def update_zproxy_configs(self, zproxy):
        # Add configs for zopereports upstream and proxy included zproxy-nginx.conf
        zopereports_proxy_conf = filter(lambda x: x.name == "/opt/zenoss/zproxy/conf/zopereports-proxy.conf", zproxy.originalConfigs)
        if not zopereports_proxy_conf:
            zproxy.originalConfigs.append(sm.ConfigFile(
                name = "/opt/zenoss/zproxy/conf/zopereports-proxy.conf",
                filename = "/opt/zenoss/zproxy/conf/zopereports-proxy.conf",
                owner = "zenoss:zenoss",
                permissions = "644",
                content = "        location ~* ^/zport/dmd/reports {\n            proxy_pass http://zopereports;\n            proxy_set_header Host $myhost;\n            proxy_http_version 1.1;\n            add_header X-Frame-Options SAMEORIGIN;\n            add_header X-XSS-Protection \"1; mode=block\";\n        }"
            ))

        zopereports_upstreams_conf = filter(lambda x: x.name == "/opt/zenoss/zproxy/conf/zopereports-upstreams.conf", zproxy.originalConfigs)
        if not zopereports_upstreams_conf:
            zproxy.originalConfigs.append(sm. ConfigFile(
               name = "/opt/zenoss/zproxy/conf/zopereports-upstreams.conf",
               filename = "/opt/zenoss/zproxy/conf/zopereports-upstreams.conf",
               owner = "zenoss:zenoss",
               permissions = "644",
               content = "server 127.0.0.1:9290;"
            ))

        # Modify zproxy configs for zenreports
        zproxy_conf_orig = filter(lambda x: x.name == "/opt/zenoss/zproxy/conf/zproxy-nginx.conf", zproxy.originalConfigs)[0]
        zproxy_conf = filter(lambda x: x.name == "/opt/zenoss/zproxy/conf/zproxy-nginx.conf", zproxy.configFiles)[0]

        # Add endpoint for new zenreports service
        zenreports_endpoint = filter(lambda x: x.name == "zenreports", zproxy.endpoints)
        if not zenreports_endpoint:
            zope_ep = filter(lambda x: x.name == "zope", zproxy.endpoints)[0]
            zenreports_ep = copy.deepcopy(zope_ep)
            zenreports_ep.name = "zenreports"
            zenreports_ep.application = "zenreports"
            zenreports_ep.applicationtemplate = "zenreports"
            zenreports_ep.portnumber = 9290
            zenreports_ep.purpose = "import_all"
            zproxy.endpoints.append(zenreports_ep)

        return self._insert_zenreport_nginx_incls(zproxy_conf_orig) and self._insert_zenreport_nginx_incls(zproxy_conf)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.error("Couldn't generate context, skipping.")
            return

        did_add_zenreports = self._add_zenreports_service(ctx)
        if not did_add_zenreports:
           return

        try:
            zope_svc = filter(lambda x: x.name == "Zope", ctx.services)[0]
            zenreports_svc = filter(lambda x: x.name == "zenreports", ctx.services)[0]
            zenreports_svc.imageID = zope_svc.imageID
        except:
            log.error("Error updating zenreports service")

        zproxy = ctx.getTopService()
        did_update_zproxy = self.update_zproxy_configs(zproxy)

        if not did_update_zproxy:
            log.error("Unable to add zenreports and update zproxy configuration")
            return

        ctx.commit()

AddReportingZopesSvcDef()
