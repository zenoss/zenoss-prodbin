#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Add usercommands to all device organizers, OsProcesses, Services, etc

$Id:$
'''
import Migrate

class ChangeEventAction(Migrate.Step):
    version = Migrate.Version(1, 1, 0)

    def cutover(self, dmd):
        dmd.Events.Change.zEventAction = 'history'

ChangeEventAction()
