##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Globals
import logging
import sys
import re
import servicemigration as sm

sm.require("1.0.0")

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
LOG = logging.getLogger("zen.migrate")

def update_mariadb_conf():

    try:
        ctx = sm.ServiceContext()
    except sm.ServiceMigrationError:
        LOG.info("Couldn't generate service context, skipping.")
        sys.exit(1)

    mariaservices = filter(lambda s: "mariadb" in s.name, ctx.services)
    LOG.info("Found {0} services with 'mariadb' in their service path".format(len(mariaservices)))
    for m in mariaservices:
        cfs = filter(lambda f: f.name == "/etc/my.cnf", m.originalConfigs + m.configFiles)
        for cf in cfs:
            if re.search("bind-address", cf.content):
                LOG.info("Nothing to update")
                break
            lines = cf.content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith("[mysqld]"):
                    updated_cfg = lines[:i+1] + [u"bind-address = 0.0.0.0"] + lines[i+1:]
                    break
            LOG.info("%s", updated_cfg)
            cf.content = '\n'.join(updated_cfg)

    # Commit our changes.
    ctx.commit()

if __name__ == '__main__':
    update_mariadb_conf()
