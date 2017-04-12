##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """AddReportingZopesSvcDef
Adds service zenreports that provides Zope instances dedicated to generating
resmgr reports.
"""
import logging
log = logging.getLogger("zen.migrate")

import os
import Migrate
import servicemigration as sm
import servicemigration.thresholdconfig
import servicemigration.threshold
import servicemigration.eventtags

import re

sm.require("1.1.6")

class AddReportingZopesSvcDef(Migrate.Step):
    """Adds a svcdef for dedicated reporting Zope"""
    version = Migrate.Version(113,0,0)

    def _add_zenreports_service(self, ctx):
        commit = False
        zenreports_svc = filter(lambda x: x.name == "zenreports", ctx.services)
        if zenreports_svc and len(zenreports_svc) > 0:
            zenreports_svc = zenreports_svc[0]
            log.info("The zenreports service already exists. Skipping this migration step.")
            return False

        jsonfile = os.path.join(os.path.dirname(__file__), "zenreports-service.json")
        with open(jsonfile) as zenreports_svcdef:
            try:
                user_interface_svc = filter(lambda x: x.name == "User Interface", ctx.services)[0]
                ctx.deployService(zenreports_svcdef.read(), user_interface_svc)
                commit = True
            except:
                log.error("Error deploying zenreports service definition")

        return commit

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate context, skipping.")
            return
        commit = False

        did_add_zenreports = self._add_zenreports_service(ctx)

        commit = did_add_zenreports

        if commit:
            ctx.commit()

AddReportingZopesSvcDef()
