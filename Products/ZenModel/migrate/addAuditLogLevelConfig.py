##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import Migrate
import os
import servicemigration as sm
from Products.ZenUtils.Utils import zenPath
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION

log = logging.getLogger("zen.migrate")
sm.require("1.1.5")

class addAuditLogLevelConfig(Migrate.Step):
    """
    Add audit log level config to service definition.
    """
    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zopes = filter(lambda s: s.name == "Zope", ctx.services)
        log.info("Found {0} services with 'Zope' in their service path".format(len(zopes)))
        commit = False

        filename = 'Products/ZenModel/migrate/data/audit_log_level.conf'
        with open(zenPath(filename)) as configFile:
            try:
                configCnt = configFile.read()
            except Exception, e:
                log.error("Error reading {0} logfilter file: {1}".format(filename, e))
                return
            auditLvlCfg = sm.ConfigFile(
                name = "/opt/zenoss/etc/audit_log_level.conf",
                filename = "/opt/zenoss/etc/audit_log_level.conf",
                owner = "zenoss:zenoss",
                permissions = "0660",
                content = configCnt
            )

        for zope in zopes:
            #if there is a audit log level config do not overwrite it
            if auditLvlCfg.name not in [cf.name for cf in zope.originalConfigs]:
                zope.originalConfigs.append(auditLvlCfg)
                commit = True
                log.info("Adding audit log level config to Zope originalConfigs")
            if auditLvlCfg.name not in [cf.name for cf in zope.configFiles]:
                zope.configFiles.append(auditLvlCfg)
                commit = True
                log.info("Adding audit log level config to Zope configFiles")
        if commit:
            ctx.commit()

addAuditLogLevelConfig()

