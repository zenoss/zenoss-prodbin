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


class UpdateZookeeperConfigs(Migrate.Step):
    "Alter zookeeper.cfg."

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zookeepers = filter(lambda s: s.name == "ZooKeeper", ctx.services)

        for zookeeper in zookeepers:

            # Update zookeeper.cfg.
            cf = filter(lambda f: f.name == "/etc/zookeeper.cfg", zookeeper.configFiles)[0]
            if cf.content.find("autopurge.snapRetainCount") < 0:
                cf.content += "\nautopurge.snapRetainCount=3"

            if cf.content.find("autopurge.purgeInterval") < 0:
                cf.content += "\nautopurge.purgeInterval=1"


        # Commit our changes.
        ctx.commit()


UpdateZookeeperConfigs()
