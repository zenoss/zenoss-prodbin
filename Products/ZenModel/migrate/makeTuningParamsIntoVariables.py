##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm

import re

from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION

sm.require("1.1.12")

ZOPES = {
  'Zauth': '/opt/zenoss/etc/zope.conf',
  'zenapi': '/opt/zenoss/etc/zenapi.conf',
  'zendebug': '/opt/zenoss/etc/zendebug.conf',
  'zenreports': '/opt/zenoss/etc/zenreports.conf',
  'Zope': '/opt/zenoss/etc/zope.conf',
}

CURRENT_SECRET_PATTERN = re.compile('session.secret[ ]*supersecret')
NEW_ZOPE_SECRET = 'session.secret          {{ getContext . "global.conf.zope-session-secret" }}'

class MakeTuningParamsIntoVariables(Migrate.Step):
    """Make Tuning Parameters Into Context Variables"""

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

	# Add variable for session secret
        top_service = ctx.getTopService()
        if "global.conf.zope-session-secret" not in top_service.context:
            top_service.context["global.conf.zope-session-secret"] = 'supersecret'
            log.info("Added session secret variable in %s service", top_service.name)

        # Update the zope session secrets to reference the variable 
        zope_services = filter(lambda s: s.name in ZOPES.keys(), ctx.services)
        for service in zope_services:

            # Update appropriate config file - don't care about orignalConfigs
            for config in filter(lambda f: f.name == ZOPES.get(service.name),service.configFiles):
               log.info("Updating session secret in config file %s for %s service", config.name, service.name)
               config.content = CURRENT_SECRET_PATTERN.sub(NEW_ZOPE_SECRET,config.content)

	# Add variable for maria max_connections and update the config file to reference it
        marialist = ['mariadb-events', 'mariadb-model']
        marias = filter(lambda s: s.name in marialist, ctx.services)
        for maria in marias:
            if "max_connections" not in maria.context:
               maria.context["max_connections"] = '1000'
               log.info("Added max_connections variable in %s service", maria.name)

            for cnf in maria.configFiles:
                if cnf.name != '/etc/my.cnf':
                    continue
                lines = cnf.content.split('\n')
                for i in range(len(lines)):
                    if lines[i].startswith('max_connections'):
                        lines[i] = 'max_connections = {{ getContext . "max_connections" }}'
			break
                cnf.content = '\n'.join(lines)

        # Add variables for zenmodeler and update the config file to reference then
        zenmodelers = filter(lambda s: s.name == 'zenmodeler', ctx.services)
        for zenmodeler in zenmodelers:
            if "parallel" not in zenmodeler.context:
               zenmodeler.context["parallel"] = '10'
               log.info("Added parallel variable in %s service", zenmodeler.name)
            if "cycletime" not in zenmodeler.context:
               zenmodeler.context["cycletime"] = '1440'
               log.info("Added cycletime variable in %s service", zenmodeler.name)
            if "startat" not in zenmodeler.context:
               zenmodeler.context["startat"] = '0 0 * * *'
               log.info("Added startat variable in %s service", zenmodeler.name)
            
            for config in filter(lambda f: f.name == '/opt/zenoss/etc/zenmodeler.conf',zenmodeler.configFiles):
               lines = config.content.split('\n')
               newLines = []
               for line in lines:
                   # Discard uncommented lines matching the variables we are changing
                   if line.startswith('parallel') or line.startswith('cycletime') or line.startswith('startat'):
                      continue
                   elif line.startswith('#parallel'):
                      newLines.append(line)
                      newLines.append('parallel {{ getContext . "parallel" }}')
                   elif line.startswith('#cycletime'):
                      newLines.append(line)
                      newLines.append('cycletime {{ getContext . "cycletime" }}')
                   elif line.startswith('#startat'):
                      newLines.append(line)
                      newLines.append('startat {{ getContext . "startat" }}')
                   else:
                      newLines.append(line)

               config.content = '\n'.join(newLines)

        # Add variables for zenhub and update the config file to reference then
        zenhubs = filter(lambda s: s.name == 'zenhub', ctx.services)
        for zenhub in zenhubs:
            if "invalidationworkers" not in zenhub.context:
               zenhub.context["invalidationworkers"] = '2'
               log.info("Added invalidationworkers variable in %s service", zenhub.name)
            if "invalidationlimit" not in zenhub.context:
               zenhub.context["invalidationlimit"] = '200'
               log.info("Added invalidationlimit variable in %s service", zenhub.name)
            
            for config in filter(lambda f: f.name == '/opt/zenoss/etc/zenhub.conf',zenhub.configFiles):
               lines = config.content.split('\n')
               newLines = []
               for line in lines:
                   # Discard uncommented lines matching the variables we are changing
                   if line.startswith('invalidationworkers') or line.startswith('invalidationlimit'):
                      continue
                   elif line.startswith('#invalidationworkers'):
                      newLines.append(line)
                      newLines.append('invalidationworkers {{ getContext . "invalidationworkers" }}')
                   elif line.startswith('#invalidationlimit'):
                      newLines.append(line)
                      newLines.append('invalidationlimit {{ getContext . "invalidationlimit" }}')
                   else:
                      newLines.append(line)
               config.content = '\n'.join(newLines)

        # Add variable for zenhubworker and update the config file to reference then
        zenhubworkers = filter(lambda s: s.name == 'zenhubworker', ctx.services)
        for zenhubworker in zenhubworkers:
            if "call-limit" not in zenhubworker.context:
               zenhubworker.context["call-limit"] = '200'
               log.info("Added call-limit variable in %s service", zenhubworker.name)

            for config in filter(lambda f: f.name == '/opt/zenoss/etc/zenhubworker.conf',zenhubworker.configFiles):
               lines = config.content.split('\n')
               newLines = []
               for line in lines:
                   # Discard uncommented lines matching the variables we are changing
                   if line.startswith('call-limit'):
                      continue
                   elif line.startswith('#call-limit'):
                      newLines.append(line)
                      newLines.append('call-limit {{ getContext . "call-limit" }}')
                   else:
                      newLines.append(line)
               config.content = '\n'.join(newLines)

        # Commit our changes.
        ctx.commit()

MakeTuningParamsIntoVariables()
