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
        zem = dmd.ZenEventManager
        conn = zem.connect()
        try:
            curs = conn.cursor()
            self.execute(curs, 'ALTER TABLE history DROP INDEX DateRange')
            self.execute(curs, 'ALTER TABLE history ADD INDEX firstTime (firstTime)')
            self.execute(curs, 'ALTER TABLE history ADD INDEX lastTime (lastTime)')
        finally: zem.close(conn)

ReindexHistory()
