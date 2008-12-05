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

__doc__="""uuidEventIds

Changes to the MySQL database to add 64-bit-hardware-compatible UUIDs.
See http://dev.zenoss.org/trac/ticket/3696 for more details.
"""

import Migrate

from MySQLdb import OperationalError
from MySQLdb.constants.ER import DUP_KEYNAME

affected_columns = [
  ('status', 'evididx', 'evid'),
  ('history', 'evididx', 'evid'),
  ('alert_state', 'evididx', 'evid'),
  ('log', 'evididx', 'evid'),
  ('detail', 'evididx', 'evid'),
]


# So why 36?
# len( str( Products.ZenUtil.guid.generate() ) ) == 36
class uuidEventIds(Migrate.Step):
    version = Migrate.Version(2, 4, 0)

    def cutover(self, dmd):
        curs = dmd.ZenEventManager.connect().cursor()
        for table, indexName, column in affected_columns:
            print "\tUpdating MySQL event table %s" % table
            try:
                curs.execute('alter table %s drop index %s ' %
                    (table, indexName))
            except OperationalError, e:
                    # Allow for aborted migrate attempts
                    print "\t\tMissing index -- previous migration " + \
                          "probably failed"

            curs.execute('alter table %s modify %s char(36) not null' %
                    (table, column))
            curs.execute('alter table %s add index %s (%s)' %
                    (table, indexName, column))

uuidEventIds = uuidEventIds()

