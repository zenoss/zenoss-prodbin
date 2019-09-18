##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import string
import Migrate
import servicemigration as sm
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION

log = logging.getLogger("zen.migrate")
sm.require("1.1.14")


class EditServiceCommand(Migrate.Step):
    "Edit service command"

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        commands = {
            "Capacity": "/opt/zenoss/bin/supervisord -n -c /opt/zenoss/etc/supervisord.conf",
            "CentralQuery": "/opt/zenoss/bin/supervisord -n -c /opt/zenoss/etc/central-query/supervisord.conf",
            "MetricConsumer": "/opt/zenoss/bin/supervisord -n -c /opt/zenoss/etc/metric-consumer-app/supervisord.conf",
            "zenhubworker (default)": "/opt/zenoss/bin/zenhubworker run -c --logfileonly --monitor {{(parent .).Name}} --workerid $CONTROLPLANE_INSTANCE_ID default",
            "zenhubworker (adm)": "/opt/zenoss/bin/zenhubworker run -c --logfileonly --monitor {{(parent .).Name}} --workerid $CONTROLPLANE_INSTANCE_ID adm",
            "zenhubiworker": "/opt/zenoss/bin/zenhubiworker run -c --duallog --hub {{(parent .).Name}} --workerid $CONTROLPLANE_INSTANCE_ID",
        }

        services = filter(lambda s: s.name in commands.keys(), ctx.services)
        for service in services:
            service.startup = commands[service.name]

        service_names = ["MetricShipper", "zminion", "zenactiond", "zeneventd", "zenimpactstate",
                    "Zauth", "Zope", "zenapi", "zenjobs", "zenjserver", "zeneventserver", "zenreports"]
        command = "/opt/zenoss/bin/supervisord -n -c /opt/zenoss/etc/{}/supervisord.conf",
        services = filter(lambda s: s.name in service_names, ctx.services)
        for service in services:
            service.startup = command.format(string.lower(service.name))

        service_names = ["zencommand", "zenjmx", "zenmodeler", "zenperfsnmp", "zenping", "zenprocess",
                    "zenpropertymonitor", "zenpython", "zenstatus", "zenwebtx"]
        command ="/opt/zenoss/bin/{} run -c --logfileonly --workers {{.Instances}} --workerid $CONTROLPLANE_INSTANCE_ID --monitor {{(parent .).Name}} "
        services = filter(lambda s: s.name in service_names, ctx.services)
        for service in services:
            service.startup = command.format(service.name)
            service.runAs = "zenoss"

        service_names = ["zentrap", "zensyslog", "zenhub"]
        command = "/opt/zenoss/bin/{} run -c --logfileonly --monitor {{(parent .).Name}} "
        for service in services:
            service.startup = command.format(service.name)
            service.runAs = "zenoss"

        ctx.commit()

EditServiceCommand()
