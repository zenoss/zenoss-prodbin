##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Migrate
import logging
import sys
import re
import servicemigration as sm

from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION

sm.require("1.0.0")

log = logging.getLogger("zen.migrate")

class AddBindAddress(Migrate.Step):
    
    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)
    

    def cutover(self, dmd):
     
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            sys.exit(1)

        mariaservices = filter(lambda s: "mariadb" in s.name, ctx.services)
        log.info("Found {0} services with 'mariadb' in their service path".format(len(mariaservices)))
        changed = False
        for m in mariaservices:
            cfs = filter(lambda f: f.name == "/etc/my.cnf", m.originalConfigs + m.configFiles)
            for cf in cfs:
                if re.search("bind-address", cf.content):
                    log.info("Nothing to update")
                    break
                lines = cf.content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith("[mysqld]"):
                        updated_cfg = lines[:i+1] + [u"bind-address = 0.0.0.0"] + lines[i+1:]
                        break
                log.info("%s", updated_cfg)
                cf.content = '\n'.join(updated_cfg)
                changed = True

        # Commit our changes.
        if changed:
            ctx.commit()

AddBindAddress()
