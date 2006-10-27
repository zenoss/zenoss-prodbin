#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Re-index the event history table.

'''

__version__ = "$Revision$"[11:-2]

import Migrate

class ReindexHistory(Migrate.Step):
    version = Migrate.Version(0, 20, 0)

    def execute(self, s, cmd):
        from MySQLdb import OperationalError
        try:
            s.execute(cmd)
        except OperationalError:
            pass

    def cutover(self, dmd):
        c = dmd.ZenEventManager.connect()
        s = c.cursor()
        self.execute(s, 'ALTER TABLE history DROP INDEX DateRange')
        self.execute(s, 'ALTER TABLE history ADD INDEX firstTime (firstTime)')
        self.execute(s, 'ALTER TABLE history ADD INDEX lastTime (lastTime)')

ReindexHistory()
