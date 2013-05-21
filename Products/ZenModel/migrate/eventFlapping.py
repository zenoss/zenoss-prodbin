##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """
Adds the /Status/Flapping event class.
"""

import Migrate
import logging
log = logging.getLogger('zen.migrate')


class EventFlappingClass(Migrate.Step):
    version = Migrate.Version(4, 2, 70)

    def cutover(self, dmd):
        dmd.Events.createOrganizer('/Status/Flapping')

EventFlappingClass = EventFlappingClass()
