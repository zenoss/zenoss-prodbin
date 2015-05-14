##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class CollectorDaemonsImportZproxy(Migrate.Step):
    "Import zproxy in all collector daemons."

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):
        ctx = sm.ServiceContext()

        # Get all services tagged "collector" and "daemon".
        collectorDaemons = filter(lambda s: all(x in s.tags for x in ["collector", "daemon"]), ctx.services)

        # Create the endpoint we're importing.
        endpoint = sm.Endpoint(
            name = "zproxy",
            purpose = "import",
            application = "zproxy",
            portnumber = 8080,
            protocol = "tcp",
            addressConfig = sm.AddressConfig(0, "")
        )

        # Add the endpoint to each daemon.
        for daemon in collectorDaemons:

            # Make sure we're not already importing zproxy.
            zpImports = filter(lambda ep: ep.name == "zproxy" and ep.purpose == "import", daemon.endpoints)
            if len(zpImports) > 0:
                continue

            daemon.endpoints.append(endpoint)

        # Commit our changes.
        ctx.commit()

CollectorDaemonsImportZproxy()
