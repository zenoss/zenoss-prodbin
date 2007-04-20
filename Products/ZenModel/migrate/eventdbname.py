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

__doc__='''EventDBName

Add database to dmd.ZenEventManager

'''
import Migrate

class EventDBName(Migrate.Step):
    version = Migrate.Version(0, 23, 0)

    def cutover(self, dmd):
        if not hasattr(dmd.ZenEventManager, 'host'):
            dmd.ZenEventManager.host = dmd.ZenEventManager.database
            dmd.ZenEventManager.database = 'events'
        if not hasattr(dmd.ZenEventHistory, 'host'):
            dmd.ZenEventHistory.host = dmd.ZenEventHistory.database
            dmd.ZenEventHistory.database = 'events'

EventDBName()
