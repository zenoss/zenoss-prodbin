import logging
import Migrate
import os
import re

import servicemigration as sm
from Products.ZenUtils.Utils import zenPath
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION

log = logging.getLogger("zen.migrate")
sm.require("1.0.0")


incl_mimetypes_pat = re.compile(r'include mime\.types;(?:(?:\\r)?\\n)?')
zauth_upstream_pat = re.compile("\\n\s+upstream zauth {\\n\s+least_conn;\\n\s+include zauth-upstreams\.conf;\\n\s+keepalive 64;\\n\s+}(?:(?:\\r)?\\n)")
zauth_upstreams_decl = '\n\n    upstream zauth {\n        least_conn;\n        include zauth-upstreams.conf;\n        keepalive 64;\n    }'
zauth_location_pat = re.compile('location .* \/zauth\/')
old_zauth_location = '\n        location ^~ /zauth/ {\n            # ZAuth requests should always be allowed\n            include zenoss-authenticated-nginx.cfg;\n            proxy_set_header Host $myhost;\n            proxy_http_version 1.1;\n            proxy_set_header  Accept-Encoding  \"\";\n        }'
new_zauth_location = '\n        location ^~ /zauth/ {\n            proxy_pass http://zauth;\n            proxy_set_header Host $myhost;\n            proxy_http_version 1.1;\n            proxy_set_header  Accept-Encoding  \"\";\n            rewrite /api/zauth/api/login /authorization/login break;\n            rewrite /zauth/api/validate /authorization/validate break;\n        }'

def find_insertion_point(conf, patterns):
    insertion_point = 0
    if len(patterns) < 1:
        return insertion_point
    for pat in patterns:
        search_result = pat.search(conf)
        if search_result is not None:
            insertion_point = max(insertion_point, search_result.end())
    return insertion_point

def insert_zauth_upstreams(conf):
    if zauth_upstream_pat.search(conf) is not None:
        return conf
    insertion_point = find_insertion_point(conf, [incl_mimetypes_pat])
    if insertion_point > 0:
        return conf[:insertion_point] + zauth_upstreams_decl + conf[insertion_point:]
    else:
        return conf

def modify_zauth_location(conf):
    if not zauth_location_pat.search(conf):
        return conf

    conf = conf.replace(old_zauth_location, new_zauth_location)
    return conf

def update_zproxy_conf(zproxy_conf):
    conf = insert_zauth_upstreams(zproxy_conf.content)
    conf = modify_zauth_location(conf)

    if conf == zproxy_conf.content:
        return False
    else:
        zproxy_conf.content = conf
        return True

class NginxConfigForZauth(Migrate.Step):
    """
    Nginx configuration change for Zauth (ZEN-28297)
    """
    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context. Skipping.")
            return

        top_service = ctx.getTopService()
        log.info("Found top level service: '{0}'".format(top_service.name))
        if top_service.name in ['Zenoss.core', 'Zenoss.resmgr.lite', 'UCS-PM.lite']:
            log.info("This top service does not need this migration. Skipping.")
            return

        changed = False

        # Change Zauth endpoint to import_all
        try:
            zauth_endpoint = [endpoint for endpoint in top_service.endpoints if endpoint.name == 'zauth'][0]
            if zauth_endpoint.purpose == 'import':
                zauth_endpoint.purpose = 'import_all'
                changed = True
        except IndexError:
            log.warn('Cannot find Zauth endpoint.')

        # Add upstream block and modify location block for zauth in the nginx configuration file
        try:
            zproxy_conf_orig = filter(
                    lambda x: x.name == "/opt/zenoss/zproxy/conf/zproxy-nginx.conf",
                    top_service.originalConfigs)[0]
            zproxy_conf = filter(
                    lambda x: x.name == "/opt/zenoss/zproxy/conf/zproxy-nginx.conf",
                    top_service.configFiles)[0]

            orig_conf_changed = update_zproxy_conf(zproxy_conf_orig)
            conf_changed = update_zproxy_conf(zproxy_conf)

            changed = changed or orig_conf_changed or conf_changed
        except IndexError:
            log.warn('Cannot find zproxy nginx configuration file in service definition.')

        if changed:
            ctx.commit()

NginxConfigForZauth()
