##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION

sm.require("1.1.12")

class FixUpdateZopeUrl(Migrate.Step):
    """Set zopeurl based on cse.tenant, rid off hardcoded domain"""

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return
        
        updated = False
        zopeUrl = 'zopeurl https://{{ getContext . "cse.tenant" }}.{{ getContext . "cse.domain" }}/{{ getContext . "cse.source" }}'
       
        # The three known places the zopeurl is defined are:
        # - zenactiond in zenactiond.conf
        # - Zope in zenactiond.conf if IncidentManagement ZP is installed
        # - zenNotify in zennotify.conf if QFramework ZP is installed
        targets = ['zenactiond','Zope','zenNotify']
        targetConfigFiles = ['/opt/zenoss/etc/zenactiond.conf','/opt/zenoss/etc/zennotify.conf']
       
        # Get list of services
        services = filter(lambda s: s.name in targets, ctx.services)

        for service in services:
           for config in filter(lambda f: f.name in targetConfigFiles,service.configFiles):
               log.info("Updating zopeurl in %s for %s", config.name, service.name)
               lines = config.content.split('\n')
               newLines = []
               for line in lines:
                   # Discard uncommented lines matching the variables we are changing
                   # Update previous migration
                   if line.startswith('zopeurl'):
                      if 'zenoss.io' in line:
                          newLines.append(zopeUrl)
                          updated = True
                      continue
                   elif (line.startswith('#zopeurl') or line.startswith('# zopeurl')):
                      newLines.append(line)
                      newLines.append(zopeUrl)
                      updated = True
                   else:
                      newLines.append(line)

               config.content = '\n'.join(newLines)

        # Commit our changes.
        if updated:
            ctx.commit()

FixUpdateZopeUrl()
