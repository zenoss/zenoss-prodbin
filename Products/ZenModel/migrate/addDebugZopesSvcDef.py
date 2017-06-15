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


sm.require("1.1.9")

mimetypes_incl_pat = re.compile(r'include mime\.types;(?:[\\r|\\n]+)?')
upstreams_block_pat = re.compile(r'\\n    upstream \w+ {[\.\\\s\w;:-]+}(?:(?:\\r)?\\n)', re.S)
map_whichzopes_block_pat = re.compile(r'\\n    map \$host \$whichzopes {[\.\*\\;\s\w~]+}(?:\\r)?\\n', re.S)
zendebug_map_clause_pat = re.compile(r'~\*zendebug debugzopes;\\n')

class AddDebugZopesSvcDef(Migrate.Step):
    """Adds a svcdef for a dedicated debug Zope instance."""
    version = Migrate.Version(114,0,0)

    def __init__(self):
        Migrate.Step.__init__(self)
        self.zendebug_upstreams_decl = '\n\n    upstream debugzopes {\n        least_conn;\n        server 127.0.0.1:9310;\n        keepalive 64;\n    }\n'
        self.zendebg_map_whichzopes_block_decl = '\n    map $host $whichzopes {\n        default zopes;\n        ~*zendebug debugzopes;\n    }\n'
        self.zendebug_proxy_incl = '        location / {\n            proxy_pass http://$whichzopes;'

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
        subprocess.check_call(['sed', '-i', 's#"ImageID": "[a-zA-Z0-9:\/]\+",#"ImageID": "{}",#'.format(zope_svc.imageID), zendebug_svc_tempfilepath])

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
        return self.zendebug_proxy_incl

    def _insertUpstreamBlockForDebugZopes(self, conf):
        intermediate_results = mimetypes_incl_pat.search(conf)
        insertion_point = intermediate_results.end()

        upstreams_blocks = [b for b in upstreams_block_pat.finditer(conf)]
        if len(upstreams_blocks) > 0:
            for b in upstreams_blocks:
                debugzope_block  = re.search(r'upstream debugzopes', b.string[b.start():b.end()])
                if debugzope_block is not None:
                    return False, None, b.end()
            insertion_point = upstreams_blocks[-1].end()

        conf_with_debugzope_upstream = conf[:insertion_point] + self.zendebug_upstreams_decl + conf[insertion_point:]
        return True, conf_with_debugzope_upstream, insertion_point + len(self.zendebug_upstreams_decl)


    def _insertMapBlockforDebugZope(self, conf, insert_pos=None):
        map_whichzopes_match = map_whichzopes_block_pat.search(conf)
        if map_whichzopes_match is None:
            if insert_pos is not None:
                insertion_point = insert_pos
            else:
                mimetypes_incl_match = mimetypes_incl_pat.search(conf)
                if mimetypes_incl_match is not None:
                    insertion_point = mimetypes_incl_match.end()
                else:
                    return False, None, 0
                upstreams_blocks = [b for b in upstreams_block_pat.finditer(conf)]
                if len(upstreams_blocks) > 0:
                    insertion_point = upstreams_blocks[-1].end()
            conf_with_map_block = conf[:insertion_point] + self.zendebg_map_whichzopes_block_decl + conf[insertion_point:]
            return True, conf_with_map_block, insertion_point + len(self.zendebg_map_whichzopes_block_decl)

        else:
            m_start, m_end = map_whichzopes_match.span()
            zdebug_clause_match = zendebug_map_clause_pat.search(conf, m_start, m_end)
            debugzopes_map_case_str = '        ~*zendebug debugzopes;\\n'
            if zdebug_clause_match is None:
                default_case_str = r'        default zopes;\\n'
                default_case_match = re.search(default_case_str, conf)
                if default_case_match is not None:
                    insertion_point = default_case_match.end()
                    conf_with_debugzope_clause = conf[:insertion_point] + debugzopes_map_case_str + conf[insertion_point:]
                    return True, conf_with_debugzope_clause, insertion_point + len(debugzopes_map_case_str)
                else:
                    return False, None, m_end
            else:
                return False, None, m_end

    def _insert_zendebug_nginx_incls(self, zproxy_conf):
        # Insert zendebug upstreams server decl
        if re.search("upstream debugzopes", zproxy_conf.content) is not None:
            return False
        did_add_upstreams_block, conf_with_upstreams, insertion_point = self._insertUpstreamBlockForDebugZopes(zproxy_conf.content)
        if not did_add_upstreams_block:
            return False
        else:
            did_add_map_block, conf_with_map_block, insertion_point = self._insertMapBlockforDebugZope(conf_with_upstreams, insert_pos=insertion_point)
            if did_add_map_block:
                zproxy_conf.content = conf_with_map_block
            else:
                return False
        zproxy_conf.content = re.sub(r'        location / {\n            proxy_pass http://zopes;', self.insertProxyDecl, zproxy_conf.content)
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

        zproxy_endpoint = filter(lambda x: x.name == "zproxy", zproxy.endpoints)[0]
        zproxy_endpoint.vhostlist.append({"Name": "zendebug", "Enabled": True})

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
