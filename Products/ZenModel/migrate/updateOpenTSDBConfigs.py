##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class UpdateOpenTSDBConfigs(Migrate.Step):
    "Change zk_quorum host from localhost to 127.0.0.1."

    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        tsdbs = filter(lambda s: "opentsdb" in ctx.getServicePath(s), ctx.services)
        tsdbs = filter(lambda s: "/opt/zenoss/etc/opentsdb/opentsdb.conf" in [i.name for i in s.originalConfigs], tsdbs)

        commit = False
        for tsdb in tsdbs:
            cf = filter(lambda f: f.name == "/opt/zenoss/etc/opentsdb/opentsdb.conf", tsdb.originalConfigs)[0]
            lines = cf.content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith("tsd.storage.hbase.zk_quorum") and "localhost" in line:
                    lines[i] = line.replace("localhost", "127.0.0.1")
                    commit = True
            cf.content = '\n'.join(lines)

        # Commit our changes.
        if commit:
            ctx.commit()

UpdateOpenTSDBConfigs()
