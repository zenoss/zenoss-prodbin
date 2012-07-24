##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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
