##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = '''
Add global.conf built by serviced to mariadb services
to have actual config instead of default
'''

import logging

log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm


class AddGlobalConfToMariadb(Migrate.Step):

    version = Migrate.Version(300, 0, 11)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return
            
        updated = False
        global_conf = sm.ConfigFile(
            name="/opt/zenoss/etc/global.conf",
            filename="/opt/zenoss/etc/global.conf",
            owner="zenoss:zenoss",
            permissions="660",
            content="# Generated by serviced\n{{range $k,$v:=contextFilter . \"global.conf.\"}}{{$k}} {{$v}}\n{{end}}"
        )

        mariadbs = filter(lambda s: s.name in ["mariadb-model", "mariadb-events"], ctx.services)
        for svc in mariadbs:
            if not [cfg for cfg in svc.originalConfigs if cfg.name == global_conf.name]:
                svc.originalConfigs.append(global_conf)
                updated = True
                log.info("Updated %s service", svc.name)
            
            if not [cfg for cfg in svc.configFiles if cfg.name == global_conf.name]:
                svc.configFiles.append(global_conf)
                updated = True
                log.info("Updated %s service", svc.name)
        
        if updated:
            ctx.commit()

AddGlobalConfToMariadb()
