##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import json
import logging
import os
import sys

import Migrate
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION
import servicemigration as sm

from . import editServicesStartUp, markHubServices

log = logging.getLogger("zen.migrate")
sm.require("1.1.14")


class AddConfigZenHubWorkerService(Migrate.Step):
    """Add the 'zenhubworker (config)' service."""

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    dependencies = [
        editServicesStartUp.instance,
        markHubServices.instance,
    ]

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Make sure the zenhubworker service hasn't already been deployed
        count = sum((
            1 for s in ctx.services if s.name == "zenhubworker (config)"
        ), 0)
        if count == 1:
            log.info(
                "zenhubworker (config) already deployed.  Skipping this step.",
            )
            return

        # Locate the 'hub' service organizers/folders.
        hubs = [
            ctx.getServiceParent(s)
            for s in ctx.services
            if s.name == "zenhub"
        ]
        hubs_migrated = 0
        for hub in hubs:
            try:
                self._deployConfigZenHubWorkerService(ctx, parent=hub)
                log.info(
                    "Deployed new config zenhubworker service  hub=%s",
                    hub.name,
                )
                log.info("Migrated '%s' hub", hub.name)
            except StopIteration:
                log.error(
                    "Hub '%s' is missing its 'zenhubworker' service. "
                    "Nothing to migrate so moving on to the next hub.",
                    hub.name,
                )
            else:
                hubs_migrated += 1

        ctx.commit()
        log.info(
            "Migrated %s of %s hub%s",
            hubs_migrated, len(hubs), "s" if len(hubs) != 1 else "",
        )

    def _deployConfigZenHubWorkerService(self, ctx, parent):
        # Load zenhubworker config
        srcConfigPath = os.path.join(
            os.path.dirname(sys.modules[__name__].__file__),
            "data/zenhubworker_v2.conf",
        )
        with open(srcConfigPath, 'r') as f:
            configContent = f.readlines()

        configContent = ''.join(configContent)

        # Load zenhubworker service template
        templatePath = os.path.join(
            os.path.dirname(sys.modules[__name__].__file__),
            "data/zenhubworker_v2.json",
        )
        with open(templatePath, 'r') as f:
            template = json.loads(f.read())

        # Load the config file into the template
        configFileName = "/opt/zenoss/etc/zenhubworker.conf"
        zproxy = ctx.getTopService()
        template["ImageID"] = zproxy.imageID
        template["ConfigFiles"][configFileName]["Content"] = configContent

        # Set the default instance count
        template["Instances"]["Default"] = 2

        # Update fields to show this worker uses the 'config' zenhub queue.
        template["Command"] = template["Command"] + " config"
        template["Name"] += " (config)"

        ctx.deployService(json.dumps(template), parent)


AddConfigZenHubWorkerService()
