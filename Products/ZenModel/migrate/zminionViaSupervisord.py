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


class RunZminionViaSupervisord(Migrate.Step):
    """Modify zminion to run via supervisord and forward logs to logstash. """

    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Create new config files
        supvd_config = sm.ConfigFile(
            name = "/opt/zenoss/etc/zminion/supervisord.conf",
            filename = "/opt/zenoss/etc/zminion/supervisord.conf",
            permissions = "644",
            content = "[supervisord]\nnodaemon=true\nlogfile = /opt/zenoss/log/supervisord.log\n\n[unix_http_server]\nfile=/tmp/supervisor.sock\n\n[supervisorctl]\nserverurl=unix:///tmp/supervisor.sock ; use a unix:// URL  for a unix socket\n\n[rpcinterface:supervisor]\nsupervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface\n\n[include]\nfiles = zminion_supervisor.conf\n"
        )
        zminion_supvd_config = sm.ConfigFile(
            name = "/opt/zenoss/etc/zminion/zminion_supervisor.conf",
            filename = "/opt/zenoss/etc/zminion/zminion_supervisor.conf",
            permissions = "644",
            content = "[program:zminion]\ncommand=/opt/zenoss/bin/zminion --minion-name zminion_{{(parent .).Name}} serve\nautorestart=true\nautostart=true\nstartsecs=5\n\n; logging\nredirect_stderr=true\nstdout_logfile_maxbytes=10MB\nstdout_logfile_backups=10\nstdout_logfile=/opt/zenoss/log/%(program_name)s.log\n"
        )

        zminion_services = filter(lambda s: s.name == 'zminion', ctx.services)
        commit = False
        for zminion in zminion_services:
            zminion.logConfigs = zminion.logConfigs or []
            logfiles = [z.path for z in zminion.logConfigs]
            log_path = "/opt/zenoss/log/zminion.log"
            if log_path not in logfiles:
                commit = True
                zminion.startup = 'su - zenoss -c "/bin/supervisord -n -c /opt/zenoss/etc/zminion/supervisord.conf"'
                zminion.logConfigs.append(sm.LogConfig(path=log_path, logType="zminion"))
            # Check for existence of log files
            if supvd_config.name not in (cf.name for cf in zminion.originalConfigs):
                commit = True
                zminion.originalConfigs.append(supvd_config)
            if zminion_supvd_config.name not in (cf.name for cf in zminion.originalConfigs):
                commit = True
                zminion.originalConfigs.append(zminion_supvd_config)

        # Commit our changes.
        if commit:
            ctx.commit()


RunZminionViaSupervisord()
