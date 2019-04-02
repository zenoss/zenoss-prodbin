##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import logging
import re
import Migrate
import servicemigration as sm

log = logging.getLogger("zen.migrate")
sm.require("1.1.11")

cfg_metrics = """\
[program:%s_metrics]
command=/usr/bin/python /opt/zenoss/bin/metrics/mysqlstats.py -d %s
autorestart=true
autostart=true
startsecs=5
"""

cfg_name = '/etc/mariadb/mariadb_supervisor.conf'

databases = {'mariadb-model': 'zodb', 'mariadb-events': 'zep'}

class addDBMetrics(Migrate.Step):
    version = Migrate.Version(300, 0, 10)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        self.commit = False

        top_service = ctx.getTopService()
        if top_service.name in ['Zenoss.core', 'Zenoss.resmgr.lite', 'UCS-PM.lite']:
            log.info("This version does not need this migration. Skipping.")
            return

        self._updateConfigs('mariadb-events', ctx)
        self._updateConfigs('mariadb-model', ctx)

        if self.commit:
            log.info("Database performance metrics added to configuration")
            ctx.commit()


    def _updateConfigs(self, database, ctx):
        service = filter(lambda s: s.name == database, ctx.services)
        if service:
            # mariadb is fixed to an single instance
            cfg_files = service[0].originalConfigs + service[0].configFiles
        else:
            log.error("Unable to locate service configuration for %s", database)
            return

        for cfg in filter(lambda f: f.name == cfg_name, cfg_files):
            existing_mysqlstats = re.search("mysqlstats", cfg.content)
            if existing_mysqlstats:
                continue

            new_cfg = []
            match = database.replace('-', "_") + "_metrics"
            lines = cfg.content.split('\n')
            for line in lines:
                if re.search(match, line):
                    # Insert above existing storage metrics
                    section = cfg_metrics % (databases[database], databases[database])
                    new_cfg.append(section)
                new_cfg.append(line)

            if len(new_cfg) != len(lines):
                cfg.content = '\n'.join(new_cfg)
                self.commit = True

addDBMetrics()
