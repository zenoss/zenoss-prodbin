import logging
import re
import Migrate
import servicemigration as sm

log = logging.getLogger("zen.migrate")
sm.require("1.1.11")

cfg_content = """\
[supervisord]
nodaemon=true
logfile = /opt/zenoss/log/memcached_supervisord.log

[unix_http_server]
file=/tmp/supervisor.sock

[supervisorctl]
serverurl=unix:///tmp/supervisor.sock ; use a unix:// URL  for a unix socket

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[program:{0}]
command=/opt/zenoss/bin/zenmemcached
autorestart=true
autostart=true
startsecs=5

[program:{0}-metrics]
command=/usr/bin/python /opt/zenoss/bin/metrics/memcachedstats.py
autorestart=true
autostart=true
startsecs=5

; logging
redirect_stderr=true
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=2
stdout_logfile=/opt/zenoss/log/%(program_name)s.log
"""

cfg_name = '/etc/memcached/memcached_supervisor.conf'
startup_command = '/bin/supervisord -n -c /etc/memcached/memcached_supervisor.conf'


class addMemcachedMetrics(Migrate.Step):
    """Add Memcached Metrics """
    version = Migrate.Version(300, 0, 12)


    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return
        top_service = ctx.getTopService()
        if top_service.name in ['Zenoss.core', 'Zenoss.resmgr.lite', 'UCS-PM.lite']:
            log.info("This version does not need this migration. Skipping.")
            return

        self.commit = False
        self._updateService(ctx, 'memcached')
        self._updateService(ctx, 'memcached-session')

        if self.commit:
            log.info("Memcached Metrics Configuration Added")
            ctx.commit()

    def _updateService(self, ctx, name):
        service = self._getService(ctx, name)
        original, config = self._getConfigs(service, cfg_name)
        content = cfg_content.format(name)
        for cfg in [original, config]:
            cfg_kind = getattr(service, cfg[0])
            if cfg[1] == None:
                self._addConfig(service, cfg_name, content, cfg_kind)
                log.info("%s: Config %s configfile, added to %s",
                         service.name, cfg_name, cfg[0])
            else:
                log.info("Existing configuration found")
                self._updateConfig(service, cfg_name, content, cfg_kind)
        # Update the startup config
        self._updateServiceCommand(service, startup_command)

    def _getService(self, ctx, name):
        return next(
            iter(filter(lambda s: s.name == name, ctx.services)), None
        )

    def _getConfigs(self, ctx, name):
        original_conf = next(
            iter(filter(lambda s: s.name == name, ctx.originalConfigs)), None
        )
        config_file = next(
            iter(filter(lambda s: s.name == name, ctx.configFiles)), None
        )
        return (('originalConfigs', original_conf), ('configFiles', config_file))

    def _updateServiceCommand(self, service, command):
        if service.startup == command:
            log.info("%s startup command already updated", service.name)
        else:
            service.startup = command
            log.info("Updated startup command for %s", service.name)

    def _addConfig(self, service, configfile, content, cfg_kind):
        new_config = sm.ConfigFile(
            name=configfile,
            filename=configfile,
            owner="zenoss:zenoss",
            permissions="0664",
            content=content
        )
        cfg_kind.append(new_config)
        self.commit = True

    def _updateConfig(self, service, configfile, content, cfg_kind):
        for config in cfg_kind:
            if config.name == configfile:
                if config.content == content:
                    log.info("Config file %s content in service %s already matches desired state",
                             configfile, service.name)
                else:
                    config.configfile.content = content
                    log.info("Updated %s config file in service %s to add Memcached metrics",
                             configfile, service.name)
                    self.commit = True

addMemcachedMetrics()
