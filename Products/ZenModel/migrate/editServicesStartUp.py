##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from collections import namedtuple

import logging
import string
import Migrate
import servicemigration as sm
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION

log = logging.getLogger("zen.migrate")
sm.require("1.1.14")


class EditServicesStartUp(Migrate.Step):
    "Edit service command"

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION) 

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        def update_service(collection):
            services = filter(lambda s: s.name in collection, ctx.services)
            for service in services:
                service.startup = command % service.name
                service.runAs = "zenoss"

        service_names = ("zencommand", "zenmodeler", "zenperfsnmp", "zenping", "zenprocess", "zenstatus")
        command = "/opt/zenoss/bin/%s run -c --logfileonly --workers {{.Instances}} --workerid $CONTROLPLANE_INSTANCE_ID --monitor {{(parent .).Name}}"

        update_service(service_names)

        service_names = ("zensyslog", "zentrap", "zenhub")
        command = "/opt/zenoss/bin/%s run -c --logfileonly --monitor {{(parent .).Name}}"

        update_service(service_names)

        svcs = {
            'zminion': 'zminion',
            'CentralQuery': 'central-query',
            'MetricConsumer': 'metric-consumer-app',
            'MetricShipper': 'metricshipper',
            'Zauth': 'zauth',
        }

        command = "/opt/zenoss/bin/supervisord -n -c /opt/zenoss/etc/{}/supervisord.conf"

        services = filter(lambda s: s.name in svcs.keys(), ctx.services)
        for service in services:
            service.startup = command.format(svcs[service.name])
            service.runAs = "zenoss"
            update_config(service)

        svcs = {
            'Zope': 'zope',
            'zenapi': 'zenapi',
            'zenreports': 'zenreports',
        }

        command = "/opt/zenoss/bin/runzope"

        services = filter(lambda s: s.name in svcs.keys(), ctx.services)
        for service in services:
            service.startup = command
            env = "CONFIG_FILE=/opt/zenoss/etc/{}.conf".format(svcs[service.name])
            if not env in service.environment:
                service.environment.append(env)
            service.runAs = "zenoss"
            
        svcs = {
            "zenhubworker (adm)": "/opt/zenoss/bin/zenhubworker run -c --logfileonly --monitor {{(parent .).Name}} --workerid $CONTROLPLANE_INSTANCE_ID adm",
            "zenhubworker (default)": "/opt/zenoss/bin/zenhubworker run -c --logfileonly --monitor {{(parent .).Name}} --workerid $CONTROLPLANE_INSTANCE_ID default",
            "zenhubiworker": "/opt/zenoss/bin/zenhubiworker run -c --duallog --hub {{(parent .).Name}} --workerid $CONTROLPLANE_INSTANCE_ID",
            "zeneventd": "/usr/bin/nice -n 10 /opt/zenoss/bin/zeneventd run -c --logfileonly ",
            "zenactiond": "/opt/zenoss/bin/zenactiond run -c --logfileonly --workerid $CONTROLPLANE_INSTANCE_ID",
            "zenjobs": "/opt/zenoss/bin/zenjobs run --logfileonly",
        }

        services = filter(lambda s: s.name in svcs.keys(), ctx.services)
        for service in services:
            service.startup = svcs[service.name]
            service.runAs = "zenoss"

        ctx.commit()


def update_central_query_conf(svc):
    cfg = filter(lambda f: f.name == "/opt/zenoss/etc/central-query/central-query_supervisor.conf", svc.originalConfigs)[0]
    cfg.content = cfg.content.replace(
        "command=bin/central-query.sh", "command=/opt/zenoss/bin/central-query.sh"
    ).replace(
        "stdout_logfile=log/%(program_name)s.log", "stdout_logfile=/opt/zenoss/log/%(program_name)s.log"
    )

def update_metric_consumer_conf(svc):
    cfg = filter(lambda f: f.name == "/opt/zenoss/etc/metric-consumer-app/metric-consumer-app_supervisor.conf", svc.originalConfigs)[0]
    cfg.content = cfg.content.replace(
        "command=bin/metric-consumer-app.sh", "command=/opt/zenoss/bin/metric-consumer-app.sh"
    ).replace(
        "stdout_logfile=log/%(program_name)s.log", "stdout_logfile=/opt/zenoss/log/%(program_name)s.log"
    )
    stopwaitsec_position = cfg.content.find("[program:metric-consumer_metrics]") - 1
    stopwaitsec = cfg.content.find("stopwaitsecs=30")
    if stopwaitsec < 0 and stopwaitsec_position > 0:
        cfg.content = cfg.content[:stopwaitsec_position] + "stopwaitsecs=30\n" + cfg.content[stopwaitsec_position:]

def update_config(svc):
    dct = {
        'CentralQuery': update_central_query_conf,
        'MetricConsumer': update_metric_consumer_conf,
    }
    fn = dct.get(svc.name, None)
    if not fn:
        return
    fn(svc)

EditServicesStartUp()
