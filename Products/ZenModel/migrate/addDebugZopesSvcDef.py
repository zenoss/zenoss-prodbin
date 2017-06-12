##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """AddDebugZopesSvcDef
Adds the service zendebug that provides Zope instances dedicated to serving non-UI JSON API requests.
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
import subprocess
import shutil


sm.require("1.1.8")

class AddDebugZopesSvcDef(Migrate.Step):
    """Adds a svcdef for dedicated a debug Zope instance"""
    version = Migrate.Version(112,0,0)

    def __init__(self):
        Migrate.Step.__init__(self)
        self.zendebug_upstreams_decl = "\n    upstream debugzopes {\n        least_conn;\n        server 127.0.0.1:9310\n        keepalive 64;\n    }\n\n    map $host $whichzopes {\n        default zopes;\n        ~*debug debugzopes;\n    }\n"
        self.zendebug_proxy_incl = "        location / {\n            proxy_pass http://$whichzopes;"

    def _add_zendebug_service(self, ctx):
        zendebug_svc = filter(lambda x: x.name == "zendebug", ctx.services)
        if zendebug_svc and len(zendebug_svc) > 0:
            log.info("The zendebug service already exists. Skipping this migration step.")
            return False

        # Copy zendebug service definition
        zendebug_svc_filepath = os.path.join(os.path.dirname(__file__), "data", "zendebug-service.json")
        zendebug_svc_tempfilepath = '/tmp/zendebug-service.json'
        shutil.copyfile(zendebug_svc_filepath, zendebug_svc_tempfilepath)

        # Substitute the ImageID
        zope_svc = filter(lambda x: x.name == "Zope", ctx.services)[0]
        # subprocess.check_call(['sed', '-i', 's#"ImageID": "[a-zA-Z0-9:\/]\+",#"ImageID": "{}",#'.format(zope_svc.imageID), zendebug_svc_tempfilepath])

        with open(zendebug_svc_tempfilepath) as zendebug_jsonfile:
            try:
                user_interface_svc = filter(lambda x: x.name == "User Interface", ctx.services)[0]
                ctx.deployService(zendebug_jsonfile.read(), user_interface_svc)
            except:
                log.error("Error deploying zendebug service definition")
                return False

        return True

    def insertUpstreamDecl(self, matchObj):
        return "{}{}".format(matchObj.group(0), self.zendebug_upstreams_decl)

    def insertProxyDecl(self, matchObj):
        return "{}{}".format(self.zendebug_proxy_incl, matchObj.group(0))

    def _insert_zendebug_nginx_incls(self, zproxy_conf):
        # Insert zendebug upstreams server decl
        if re.search("upstream debugzopes", zproxy_conf.content) is not None:
            return False
        zproxy_conf_a = re.sub(r'mime\.types;[\\nr]+\s+(?:(?:upstream\s+[\w-]+\s{[\.\s\\\w;-]+})(?:[\\rn]+\s+)*)*', self.insertUpstreamDecl, zproxy_conf.content)
        zproxy_conf_b = re.sub(r'        location / {\n            proxy_pass http://zopes;', self.insertProxyDecl, zproxy_conf_a)
        zproxy_conf.content = zproxy_conf_b
        return True

    def update_zproxy_configs(self, zproxy):

        # Modify zproxy configs for zendebug
        zproxy_conf_orig = filter(lambda x: x.name == "/opt/zenoss/zproxy/conf/zproxy-nginx.conf", zproxy.originalConfigs)[0]
        zproxy_conf = filter(lambda x: x.name == "/opt/zenoss/zproxy/conf/zproxy-nginx.conf", zproxy.configFiles)[0]

        # Add endpoint for new zendebug service
        zendebug_endpoint = filter(lambda x: x.name == "zendebug", zproxy.endpoints)
        if not zendebug_endpoint:
            zope_ep = filter(lambda x: x.name == "zope", zproxy.endpoints)[0]
            zendebug_ep = copy.deepcopy(zope_ep)
            zendebug_ep.name = "zendebug"
            zendebug_ep.application = "zendebug"
            zendebug_ep.applicationtemplate = "zendebug"
            zendebug_ep.portnumber = 9310
            zendebug_ep.purpose = "import_all"
            zproxy.endpoints.append(zendebug_ep)

        return self._insert_zendebug_nginx_incls(zproxy_conf_orig) and self._insert_zendebug_nginx_incls(zproxy_conf)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.error("Couldn't generate context, skipping.")
            return

        did_add_zendebug = self._add_zendebug_service(ctx)
        if not did_add_zendebug:
           return

        zproxy = ctx.getTopService()
        did_update_zproxy = self.update_zproxy_configs(zproxy)

        if not did_update_zproxy:
            log.error("Unable to add zendebug and update zproxy configuration")
            return

        ctx.commit()

AddDebugZopesSvcDef()
