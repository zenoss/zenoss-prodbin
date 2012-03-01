###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

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
