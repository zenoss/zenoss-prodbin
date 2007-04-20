###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

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
