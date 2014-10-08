##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

"""
This module patches relstorage.adapters.mysql.MySQLdbConnectionManager to
record the process ID and (python) thread ID to the connection_info database
table every time open() is called.
"""

import os
import sys
import thread
import logging
import traceback
from Products.ZenUtils.Utils import monkeypatch

LOG = logging.getLogger("zen.relstorage.mysql")

_record_pid_sql = (
    "replace into connection_info(connection_id, pid, info, ts) "
    "select connection_id(), %s, %s, current_timestamp")
def record_pid(conn, cursor):
    try:
        conn.autocommit(True)
        pid = os.getpid()
        tid = thread.get_ident()
        cmd = ' '.join(sys.argv)
        stacktrace = ''.join(traceback.format_stack())
        info = "pid=%d tid=%d\n%s\n%s" % (pid, tid, cmd, stacktrace)
        cursor.execute(_record_pid_sql, (pid, info))
        conn.autocommit(False)
    except:
        LOG.debug("Unable to record pid and thread_id to connection_info",
                 exc_info=True)

try:
    from relstorage.adapters.schema import MySQLSchemaInstaller
    @monkeypatch('relstorage.adapters.mysql.MySQLdbConnectionManager')
    def open(self, *args, **kwargs):
        conn, cursor = original(self, *args, **kwargs)
        record_pid(conn, cursor)
        return conn, cursor

    @monkeypatch('relstorage.adapters.schema.MySQLSchemaInstaller')
    def create(self, cursor):
        super(MySQLSchemaInstaller, self).create(cursor)
        self.create_connection_info(cursor)

    @monkeypatch('relstorage.adapters.schema.MySQLSchemaInstaller')
    def update_schema(self, cursor, tables):
        super(MySQLSchemaInstaller, self).update_schema(cursor, tables)
        if not "connection_info" in tables:
            self.create_connection_info(cursor)

    @monkeypatch('relstorage.adapters.schema.MySQLSchemaInstaller')
    def create_connection_info(self, cursor):
        script = """
            CREATE TABLE IF NOT EXISTS connection_info(
            connection_id INT NOT NULL,
            pid INT NOT NULL,
            info VARCHAR(60000) NOT NULL,
            ts TIMESTAMP NOT NULL,
            PRIMARY KEY(connection_id),
            KEY(pid)
          ) ENGINE = MyISAM;
        """
        self.runner.run_script(cursor, script)

except ImportError:
    pass

