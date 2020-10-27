##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging
log = logging.getLogger("zen.migrate")

from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class AddVarbindCopyMode(Migrate.Step):

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)
    
    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        update_string = """# Varbind copy mode. 
# Assume we have the following varbinds:
#    someVar.0  Data0
#    someVar.1  Data1
# Possible copy modes:
# 0 - the varbinds are copied into event as one
#     field. Expected event fields:
#         someVar:         Data0,Data1
#         someVar.ifIndex: 0,1
# 1 - the varbinds are copied into event as several
#     fields and sequence field is added. 
#     Expected event fields:
#         someVar.0:        Data0
#         someVar.1:        Data1
#         someVar.sequence: 0,1
# 2 - the mixed mode. Uses varbindCopyMode=0 behaviour
#     if there is only one occurrence of the varbind, 
#     otherwise uses varbindCopyMode=1 behaviour
#varbindCopyMode 2
#
"""

        log.info("Updating zentraps configuration file with --varbindCopyMode option.")

        commit = False
        zentraps = filter(lambda z: z.name == "zentrap", ctx.services)

        log.info("Found %i services named 'zentrap'.", len(zentraps))

        for zentrap in zentraps:
            configfiles = zentrap.originalConfigs + zentrap.configFiles
            current_config = "/opt/zenoss/etc/{}.conf".format(zentrap.name)
            for configfile in filter(lambda f: f.name == current_config, configfiles):
                if 'varbindCopyMode' in configfile.content:
                    log.debug("varbindCopyMode option already included in config")
                    continue
                log.info("Appending varbindCopyMode option to %s for '%s'.", current_config, zentrap.name)
                configfile.content += update_string
                commit = True

        if commit:
            ctx.commit()


AddVarbindCopyMode()
