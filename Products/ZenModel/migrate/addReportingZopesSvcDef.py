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


sm.require("1.1.6")

class AddReportingZopesSvcDef(Migrate.Step):
    """Adds a svcdef for dedicated reporting Zope"""
    version = Migrate.Version(113,0,0)

    def _add_zenreports_service(self, ctx):
        commit = False
        zenreports_svc = filter(lambda x: x.name == "zenreports", ctx.services)
        if zenreports_svc and len(zenreports_svc) > 0:
            zenreports_svc = zenreports_svc[0]
            log.info("The zenreports service already exists. Skipping this migration step.")
            return False

        jsonfile = os.path.join(os.path.dirname(__file__), "zenreports-service.json")
        with open(jsonfile) as zenreports_svcdef:
            try:
                user_interface_svc = filter(lambda x: x.name == "User Interface", ctx.services)[0]
                ctx.deployService(zenreports_svcdef.read(), user_interface_svc)
                commit = True
            except:
                log.error("Error deploying zenreports service definition")

        return commit

    def insertUpstreamDecl(self, matchObj):
        zenreports_upstreams_decl = "    upstream zopereports {\n        least_conn;\n        include zopereports-upstreams.conf;\n        keepalive 64;\n    }"
        return matchObj.group(0)+ '\n' + zenreports_upstreams_decl

    def insertProxyDecl(self, matchObj):
        zenreports_proxy_incl = "\n        include zopereports-proxy.conf;\n\n"
        return "{}{}".format(zenreports_proxy_incl, matchObj.group(0))

    def _insert_zenreport_nginx_incls(self, zproxy_conf):
        # Insert zenreports upstreams server decl
        zenreports_upstreams_decl = "    upstream zopereports {\n        least_conn;\n        include zopereports-upstreams.conf;\n        keepalive 64;\n    }\n"
        if re.search(zenreports_upstreams_decl, zproxy_conf.content) is not None:
            return False
        zenreports_proxy_incl = "\r\n        include zopereports-proxy.conf;\n\n"
        if re.search(zenreports_proxy_incl, zproxy_conf.content) is not None:
            return False
        zproxy_conf_a = re.sub('include mime.types;', self.insertUpstreamDecl, zproxy_conf.content)
        zproxy_conf_b = re.sub(r'        location / {', self.insertProxyDecl, zproxy_conf_a)
        zproxy_conf.content = zproxy_conf_b
        if re.search(zenreports_proxy_incl, zproxy_conf.content) is None:
            log.info("!!! Include for zenreports proxy is not present!")
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

        #Modify zproxy configs for zenreports
        zproxy_conf_orig = filter(lambda x: x.name == "/opt/zenoss/zproxy/conf/zproxy-nginx.conf", zproxy.originalConfigs)[0]
        zproxy_conf = filter(lambda x: x.name == "/opt/zenoss/zproxy/conf/zproxy-nginx.conf", zproxy.configFiles)[0]

        #Add endpoint for new zenreports service
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
            log.info("Couldn't generate context, skipping.")
            return
        commit = False

        did_add_zenreports = self._add_zenreports_service(ctx)
        if did_add_zenreports:
            try:
                zope_svc = filter(lambda x: x.name == "Zope", ctx.services)[0]
                zenreports_svc = filter(lambda x: x.name == "zenreports", ctx.services)[0]
                zenreports_svc.imageID = zope_svc.imageID
            except:
                log.error("Error updating zenreports service")

        zproxy = ctx.getTopService()
        did_update_zproxy = self.update_zproxy_configs(zproxy)
        commit = did_add_zenreports and did_update_zproxy

        if commit:
            ctx.commit()

AddReportingZopesSvcDef()
