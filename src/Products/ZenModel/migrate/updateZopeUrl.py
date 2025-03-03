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

sm.require("1.1.12")

class UpdateZopeUrl(Migrate.Step):
    """Set zopeurl based on cse.tenant and cse.source"""

    version = Migrate.Version(300, 0, 10)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

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
                   if line.startswith('zopeurl'):
                      continue
                   elif (line.startswith('#zopeurl') or line.startswith('# zopeurl')):
                      newLines.append(line)
                      newLines.append('zopeurl https://{{ getContext . "cse.tenant" }}.zenoss.io/{{ getContext . "cse.source" }}')
                   else:
                      newLines.append(line)

               config.content = '\n'.join(newLines)

        # Commit our changes.
        ctx.commit()

UpdateZopeUrl()
