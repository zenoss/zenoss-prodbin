#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################
__doc__='Add eventClassMapping to status and history tables'

import logging
log = logging.getLogger("zen.migrate")

import Migrate

class EventClassMapping(Migrate.Step):
    version = Migrate.Version(1, 2, 0)

    def cutover(self, dmd):
        conn = dmd.ZenEventManager.connect()
        try:
            tables = ('status', 'history')
            cur = conn.cursor()
            for table in tables:
                cur.execute('desc %s' % table)
                r = cur.fetchall()
                if not [f for f in r if f[0] == 'eventClassMapping']:
                    cur.execute('alter table %s ' % table +
                                'add column eventClassMapping '
                                'varchar(128) default ""')
        finally:
            conn.close()
EventClassMapping()
