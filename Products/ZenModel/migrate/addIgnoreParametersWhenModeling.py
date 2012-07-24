##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """Move some parameters from zeneventserver.conf to ZepConfig so
changing them doesn't require a restart.
"""
import logging
import Globals
from Products.ZenUtils.Utils import unused
from Products.ZenModel.migrate import Migrate

unused(Globals)

log = logging.getLogger('zen.migrate')

class addIgnoreParametersWhenModeling(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        log.info("Adding ignoreParametersWhenModeling to all process classes.")
        for process_class in dmd.Processes.getSubOSProcessClassesSorted():
            process_class.setZenProperty("addIgnoreParametersWhenModeling", False)

addIgnoreParametersWhenModeling()
