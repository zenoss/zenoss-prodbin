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


class AddPIDFiles(Migrate.Step):
    "Add PIDFiles to services"

    version = Migrate.Version(300, 0, 11)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        service_names = ['zencommand', 'zenjmx', 'zenmodeler', 'zenperfsnmp',
                         'zenping', 'zenprocess', 'zenpropertymonitor',
                         'zenpython', 'zenstatus', 'zensyslog', 'zentrap',
                         'zenwebtx']
        services = filter(lambda s: s.name in service_names, ctx.services)
        for service in services:
            service.pidFile = "exec echo $ZENHOME/var/$SERVICE-$MONITOR.pid"

        pidFiles = {
        "zenhub": "exec echo $ZENHOME/var/zenhub-{{(parent .).Name}}.pid",
        "zenhubiworker": "exec echo $ZENHOME/var/worker-{{(parent .).Name}}.pid",
        "zenhubworker (adm)": "exec echo $ZENHOME/var/zenhubworker-{{(parent .).Name}}.pid",
        "zenhubworker (default)": "exec echo $ZENHOME/var/zenhubworker-{{(parent .).Name}}.pid",
        "Impact": "exec echo /opt/zenoss_impact/var/zenoss_impact.pid",
        }

        services = filter(lambda s: s.name in pidFiles.keys(), ctx.services)
        for service in services:
            service.pidFile = pidFiles[service.name]
        ctx.commit()

AddPIDFiles()
