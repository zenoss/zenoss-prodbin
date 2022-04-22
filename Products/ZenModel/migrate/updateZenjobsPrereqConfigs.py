##############################################################################
#
# Copyright (C) Zenoss, Inc. 2022, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
This updates zenjob configs for proper job running after the catalogs are available
"""

import logging
import Migrate
import servicemigration as sm
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION

log = logging.getLogger("zen.migrate")


class UpdateZenjobsPrereqConfigs(Migrate.Step):
    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return
        service = filter(lambda s: s.name == "zenjobs", ctx.services)[0]
        solrRrereqs = "Solr answering"
        solrScript = 'curl -A \'Solr answering prereq\' -s http://localhost:8983/solr/zenoss_model/admin/ping?wt=json | grep -q \'"status":"OK"\''
        if len(filter(lambda x: x.name == solrRrereqs, service.prereqs)) == 0:
            service.prereqs.append(sm.prereq.Prereq(name=solrRrereqs, script=solrScript))
        ctx.commit()


UpdateZenjobsPrereqConfigs()