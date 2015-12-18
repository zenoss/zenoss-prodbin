##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class zenmodelerWorkers(Migrate.Step):
    "Add worker options to zenmodeler."

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):
        # Don't apply this migration to core.
        if dmd.getProductName() == "core":
            return

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Get all zenmodeler services.
        commit = False
        modelers = filter(lambda s: s.name == "zenmodeler", ctx.services)

        # Alter their startup command and instanceLimits.
        for modeler in modelers:
            new_startup = "su - zenoss -c \"/opt/zenoss/bin/zenmodeler run -c --logfileonly --workers {{.Instances}} --workerid $CONTROLPLANE_INSTANCE_ID --monitor {{(parent .).Name}} \""
            if modeler.startup != new_startup:
                modeler.startup = new_startup
                commit = True
            if (modeler.instanceLimits.minimum, modeler.instanceLimits.maximum) != (1, None):
                modeler.instanceLimits.minimum = 1
                modeler.instanceLimits.maximum = None
                commit = True

        # Commit our changes.
        if commit:
            ctx.commit()


zenmodelerWorkers()
