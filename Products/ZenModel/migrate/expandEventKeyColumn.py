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

Increase eventKey length from 64 to 128 characters.

'''
import Migrate

import logging
log = logging.getLogger("zen.migrate")

class ExpandEventKeyColumn(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
        conn = dmd.ZenEventManager.connect()
        c = conn.cursor()
        for table in ('history', 'status'):
            c.execute('describe %s' % (table,))
            for col in c.fetchall():
                if col[0] == 'eventKey' and col[1] == 'varchar(64)':
                    c.execute('alter table %s modify eventKey varchar(128)' %
                            (table,))


ExpandEventKeyColumn()
