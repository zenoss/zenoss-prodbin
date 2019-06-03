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
    """Set zopeurl based on cse.tenant"""

    version = Migrate.Version(300, 0, 11)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        targets = ['zenactiond']
        # if IncMan ZP is installed also set zopeurl in zope zenactiond.conf
        try:
            pack = dmd.ZenPackManager.packs._getOb('ZenPacks.zenoss.IncidentManagement')
            targets.append('Zope')
        except:
            log.info("Skipping setting zopeurl in zenactiond.conf in zope since IncidentManagement ZP is not installed")

	# Set zopeurl in zenactiond.conf of target services
        services = filter(lambda s: s.name in targets, ctx.services)

        for service in services:
            for config in filter(lambda f: f.name == '/opt/zenoss/etc/zenactiond.conf',service.configFiles):
               log.info("Updating zopeurl in zenactiond.conf for %s",service.name)
               lines = config.content.split('\n')
               newLines = []
               for line in lines:
                   # Discard uncommented lines matching the variables we are changing
                   if line.startswith('zopeurl'):
                      continue
                   elif (line.startswith('#zopeurl') or line.startswith('# zopeurl')):
                      newLines.append(line)
                      newLines.append('zopeurl https://{{ getContext . "cse.tenant" }}.zenoss.io')
                   else:
                      newLines.append(line)

               config.content = '\n'.join(newLines)

        # Commit our changes.
        ctx.commit()

UpdateZopeUrl()
