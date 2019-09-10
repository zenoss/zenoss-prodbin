##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import Migrate
import servicemigration as sm

log = logging.getLogger("zen.migrate")
sm.require("1.1.13")


class EditServiceCommand(Migrate.Step):
    "Edit service command"

    version = Migrate.Version(300, 0, 11)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        commands = {
        "Capacity": "/bin/bash -c \"cp /opt/zenoss/etc/capacity/capacity_supervisor.conf.in /opt/zenoss/etc/capacity/capacity_supervisor.conf; sed -i 's@%INSTANCES%@{{.Instances}}@g;' /opt/zenoss/etc/capacity/capacity_supervisor.conf; /opt/zenoss/bin/supervisord -n -c /opt/zenoss/etc/capacity/supervisord.conf\"",
        "MetricShipper": "/bin/supervisord -n -c /opt/zenoss/etc/metricshipper/supervisord.conf",
        "zminion": "/bin/supervisord -n -c /opt/zenoss/etc/zminion/supervisord.conf",
        "zenactiond": "/opt/zenoss/bin/supervisord -n -c /opt/zenoss/etc/zenactiond/supervisord.conf",
        "zeneventd": "/opt/zenoss/bin/supervisord -n -c /opt/zenoss/etc/zeneventd/supervisord.conf",
        "zeneventserver": "/bin/bash -c \"cp /opt/zenoss/etc/zeneventserver/zeneventserver_supervisor.conf.in /opt/zenoss/etc/zeneventserver/zeneventserver_supervisor.conf; sed -i 's@%RAM_COMMITMENT%@{{.RAMCommitment}}@g;' /opt/zenoss/etc/zeneventserver/zeneventserver_supervisor.conf; /opt/zenoss/bin/supervisord -n -c /opt/zenoss/etc/zeneventserver/supervisord.conf\"",
        "zenimpactstate": "/opt/zenoss/bin/supervisord -n -c /opt/zenoss/etc/zenimpactstate/supervisord.conf",
        "CentralQuery": "/opt/zenoss/bin/supervisord -n -c /opt/zenoss/etc/central-query/supervisord.conf",
        "MetricConsumer": "/opt/zenoss/bin/supervisord -n -c /opt/zenoss/etc/metric-consumer-app/supervisord.conf",
        "MetricShipper": "/opt/zenoss/bin/supervisord -n -c /opt/zenoss/etc/metricshipper/supervisord.conf",
        "Zauth": "/opt/zenoss/bin/supervisord -n -c /opt/zenoss/etc/zauth/supervisord.conf",
        "Zope": "/opt/zenoss/bin/supervisord -n -c /opt/zenoss/etc/zope/supervisord.conf",
        "zenapi": "/opt/zenoss/bin/supervisord -n -c /opt/zenoss/etc/zenapi/supervisord.conf",
        "zenjobs": "/opt/zenoss/bin/supervisord -n -c /opt/zenoss/etc/zenjobs/supervisord.conf",
        "zenjserver": "/opt/zenoss/bin/supervisord -n -c /opt/zenoss/etc/zenjserver/supervisord.conf",
        "zenreports": "/opt/zenoss/bin/supervisord -n -c /opt/zenoss/etc/zenreports/supervisord.conf",
        }

        services = filter(lambda s: s.name in commands.keys(), ctx.services)
        for service in services:
            service.startup = commands[service.name]
        ctx.commit()

EditServiceCommand()
