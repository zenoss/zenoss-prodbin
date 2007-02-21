#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################
__doc__='Convert MEMORY tables to INNODB'

import logging
log = logging.getLogger("zen.migrate")

import Migrate

class Innodb(Migrate.Step):
    version = Migrate.Version(1, 0, 0)

    def cutover(self, dmd):
        from Products.ZenEvents.DbConnectionPool import DbConnectionPool
        cpool = DbConnectionPool()
        conn = cpool.get(backend=self.dmd.ZenEventManager.backend, 
                        host=self.dmd.ZenEventManager.host, 
                        port=self.dmd.ZenEventManager.port, 
                        username=self.dmd.ZenEventManager.username, 
                        password=self.dmd.ZenEventManager.password, 
                        database=self.dmd.ZenEventManager.database)
        curs = conn.cursor()
        try:
            curs.execute('SHOW TABLE STATUS')
            for row in curs.fetchall():
                table, engine = row[:2]
                options = row[-2]
                if engine == 'MEMORY':
                    log.debug('Converting table %s' % table)
                    curs.execute('ALTER TABLE %s ENGINE=INNODB' % table)
                if options and options.find('max_rows=') >= 0:
                    curs.execute('ALTER TABLE %s max_rows=0' % table)
        finally:
            curs.close()
            cpool.put(conn)

Innodb()
