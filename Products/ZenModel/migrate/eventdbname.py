#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''EventDBName

Add database to dmd.ZenEventManager

'''
import Migrate

class EventDBName(Migrate.Step):
    version = 24.0

    def cutover(self, dmd):
        if not hasattr(dmd.ZenEventManager, 'host'):
            dmd.ZenEventManager.host = dmd.ZenEventManager.database
            dmd.ZenEventManager.database = 'events'
        if not hasattr(dmd.ZenEventHistory, 'host'):
            dmd.ZenEventHistory.host = dmd.ZenEventHistory.database
            dmd.ZenEventHistory.database = 'events'

EventDBName()
