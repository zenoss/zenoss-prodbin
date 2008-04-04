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

Changes to the MySQL database for zenoss 2.2

'''

import Migrate

from MySQLdb import OperationalError
from MySQLdb.constants.ER import DUP_KEYNAME

class TwoTwoMySqlChanges(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
        curs = dmd.ZenEventManager.connect().cursor()
        for table, indexName, column in [
                ('status', 'deviceidx', 'device'),
                ('status', 'severityidx', 'severity'),
                ('history', 'severityidx', 'severity'),
                ]:
            try:
                curs.execute('alter table %s add index %s (%s)' %
                    (table, indexName, column))
            except OperationalError, e:
                if e[0] == DUP_KEYNAME:
                    pass
                else:
                    raise

twoTwoMySqlChanges = TwoTwoMySqlChanges()
