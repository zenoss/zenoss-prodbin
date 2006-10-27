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
        c = dmd.ZenEventManager.connect()
        try:
            s = c.cursor()
            s.execute('SHOW TABLE STATUS')
            for row in s.fetchall():
                table, engine = row[:2]
                options = row[-2]
                if engine == 'MEMORY':
                    log.debug('Converting table %s' % table)
                    s.execute('ALTER TABLE %s ENGINE=INNODB' % table)
                if options and options.find('max_rows=') >= 0:
                    s.execute('ALTER TABLE %s max_rows=0' % table)
        finally:
            c.close()
Innodb()
