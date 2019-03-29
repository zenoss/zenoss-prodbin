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
import servicemigration as sm

log = logging.getLogger("zen.migrate")
sm.require("1.1.0")

__doc__='''
Update zeneventserver to use supervisord and add a config file.
In addition, also update the supervisor config file for CentralQuery and MetricConsumer
'''

_CentralQueryConfigContent = """\
[program:central-query]
command=bin/central-query.sh
autorestart=true
autostart=true
startsecs=5
environment=JVM_ARGS="-Xmx{{bytesToMB .RAMCommitment}}m"

[program:central-query_metrics]
command=/usr/bin/python /opt/zenoss/bin/metrics/jvmstats.py
autorestart=true
autostart=true
startsecs=5

; logging
redirect_stderr=true
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=2
stdout_logfile=log/%(program_name)s.log
"""

_MetricConsumerConfigContent = """\
[program:metric-consumer-app]
command=bin/metric-consumer-app.sh
autorestart=true
autostart=true
startsecs=5
environment=JVM_ARGS="-Xmx{{bytesToMB .RAMCommitment}}m"

[program:metric-consumer_metrics]
command=/usr/bin/python /opt/zenoss/bin/metrics/jvmstats.py
autorestart=true
autostart=true
startsecs=5

; logging
redirect_stderr=true
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=2
stdout_logfile=log/%(program_name)s.log
"""

_ZENEVENTSERVERCOMMAND = "su - zenoss -c \"cd /opt/zenoss && /bin/supervisord -n -c /opt/zenoss/etc/zeneventserver_supervisord.conf\""
_ZenEventServerConfigContent = """\
[supervisord]
nodaemon=true
logfile = log/supervisord.log

[unix_http_server]
file=/tmp/supervisor.sock

[supervisorctl]
serverurl=unix:///tmp/supervisor.sock ; use a unix:// URL  for a unix socket

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[program:zeneventserver]
command=bin/zeneventserver run_quiet
priority=1
autorestart=true
autostart=true
startsecs=5
environment=DEFAULT_ZEP_JVM_ARGS="-server -Xmx{{.RAMCommitment}}"

[program:zeneventserver_metrics]
command=/usr/bin/python bin/metrics/zepjvmstats.py
autorestart=true
autostart=true
startsecs=5

; logging
redirect_stderr=true
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=2
stdout_logfile=log/%(program_name)s.log
"""

class CollectJVMMetrics(Migrate.Step):
    version = Migrate.Version(300, 0, 9)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context. Skipping.")
            return

        zeneventserver = self._getService(ctx, "zeneventserver")
        self._updateServiceCommand(zeneventserver,_ZENEVENTSERVERCOMMAND)
        self._addConfig(zeneventserver,"/opt/zenoss/etc/zeneventserver_supervisord.conf",_ZenEventServerConfigContent)

        centralquery = self._getService(ctx, "CentralQuery")
        self._updateConfig(centralquery,"/opt/zenoss/etc/central-query/central-query_supervisor.conf",_CentralQueryConfigContent)

        metricconsumer = self._getService(ctx, "MetricConsumer")
        self._updateConfig(metricconsumer,"/opt/zenoss/etc/metric-consumer-app/metric-consumer-app_supervisor.conf",_MetricConsumerConfigContent)

        ctx.commit()

    def _getService(self, ctx, name):
        return next(
            iter(filter(lambda s: s.name == name, ctx.services)), None
        )

    def _getConfigs(self, ctx, name):
        # We don't care about original configs
        config_file = next(
            iter(filter(lambda s: s.name == name, ctx.configFiles)), None
        )
        return config_file

    def _updateServiceCommand(self, service, command):
        if service.startup == command:
            log.info("%s startup command already updated", service.name)
        else:
            service.startup = command
            log.info("Updated startup command for %s", service.name)

    def _addConfig(self, service, configFile, content):
        config = self._getConfigs(service, configFile)
        if config:
            log.info("Service %s configFiles already has %s",service.name, config.name)
        else:
           new_config = sm.ConfigFile(
               name=configFile,
               filename=configFile,
               owner="zenoss:zenoss",
               permissions="0664",
               content=content
           )
           service.configFiles.append(new_config)
           log.info("Added %s config to service %s configFiles",new_config.name, service.name)

    def _updateConfig(self, service, configFile, content):
        config = self._getConfigs(service, configFile)

        if config.content == content:
           log.info(
               log.info("Config file %s content in service %s already matches desired state", configFile, service.name)
           )
        else:
           config.content = content
           log.info("Updated %s config file in service %s to add JVM metrics", configFile, service.name)

CollectJVMMetrics()
