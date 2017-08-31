##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import re
import logging
log = logging.getLogger("zen.migrate")

from Products.ZenUtils.Utils import zenPath

import Migrate
import servicemigration as sm
from servicemigration import InstanceLimits
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION

sm.require("1.1.10")


class AddMariaDBLogFilters(Migrate.Step):
    """Add LogFilters for MariaDB (ZEN-28087)"""

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        top = ctx.getTopService()
        log.info("Found top level service: '{0}'".format(top.name))
        if top.name.find("Zenoss") != 0 and top.name.find("UCS-PM") != 0:
            log.info("Top level service name isn't Zenoss or UCS-PM; skipping.")
            return

        services = filter(lambda s: s.name in ["mariadb"], ctx.services)
        log.info("Found %d mariadb services," % len(services))

        filterName = "mariadb"
        for service in services:
            servicePath = ctx.getServicePath(service)
            for logConfig in service.logConfigs:
                if logConfig.logType == "mariadb":
                    if not logConfig.filters:
                        log.info("Adding logfilter for {0}".format(logConfig.logType))
                        logConfig.filters = [filterName]
                    else:
                        log.info("No updates necessary for the logfilter for {0}".format(logConfig.logType))

        ctx.commit()

AddMariaDBLogFilters()
