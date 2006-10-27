#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Migration for ActionRule Schedule Objects

'''

__version__ = "$Revision$"[11:-2]

import os
import Migrate
import Globals

from Products.ZenEvents.ActionRule import ActionRule

class ARSchedule(Migrate.Step):
    "Convert a data source into a data source with a data point"
    version = Migrate.Version(0, 23, 0)

    def __init__(self):
        Migrate.Step.__init__(self)

    def cutover(self, dmd):
        for u in dmd.ZenUsers.getAllUserSettings():
            for ar in u.objectValues(spec='ActionRule'):
                ar.buildRelations()

ARSchedule()
