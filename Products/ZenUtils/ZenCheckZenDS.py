#!/opt/zenoss/bin/python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import Globals
import sys
from optparse import OptionParser
from subprocess import Popen, PIPE
from Products.ZenUtils.Utils import zenPath
import re
import logging

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("zen.zencheckzendb")

class Main(object):

    def install(self, databases=[], silent=False):
        if not databases: databases = ['zodb', 'zodb_session']
        script = zenPath("Products", "ZenUtils", "relstorage", "mysql", "003.sql")
        with open(script, 'r') as f: sql = f.read()
        for database in databases:
            stdout, stderr = self._zendb(database, sql)
            if not silent:
                LOG.warn("Installed into '%s' database. PLEASE RESTART ALL DEPENDENT SERVICES." % (database,))

        tables = ["%s.connection_info" % db for db in databases]
        pid = "coalesce(%s)" % ', '.join(["%s.pid" % t for t in tables])
        info = "coalesce(%s)" % ', '.join(["%s.info" % t for t in tables])
        sql = """
        DROP PROCEDURE IF EXISTS mysql.KillTransactions;
        DELIMITER //
          CREATE PROCEDURE mysql.KillTransactions(IN longer_than_num_seconds int(10) unsigned, IN action varchar(10))
          BEGIN

            DECLARE _txns_count INT DEFAULT 0;
            DECLARE _txns_killed TEXT DEFAULT "'HOST','DB','COMMAND','STATE','INFO','PID','LINE1','LINE2','TRX_ID','TRX_QUERY','TRX_STARTED','TRX_MYSQL_THREAD_ID'";
            DECLARE v_host varchar(54);
            DECLARE v_db varchar(64);
            DECLARE v_command varchar(16);
            DECLARE v_state varchar(64);
            DECLARE v_info longtext;
            DECLARE v_pid bigint(21) unsigned;
            DECLARE v_line1 varchar(1000);
            DECLARE v_line2 varchar(1000);
            DECLARE v_trx_id varchar(20);
            DECLARE v_trx_query varchar(1024);
            DECLARE v_started varchar(20);
            DECLARE v_thread_id bigint(21) unsigned;
            DECLARE done BOOL DEFAULT FALSE;
            DECLARE c_thread_id CURSOR FOR
              select
                  p.host,
                  p.db,
                  p.command,
                  p.state,
                  p.info,
                  %s as pid,
                  substring_index(%s,'\n',1) as line1,
                  substring_index(substring_index(%s,'\n',2),'\n',-1) as line2,
                  trx.trx_id,
                  trx.trx_query,
                  trx.trx_started,
                  trx.trx_mysql_thread_id
              from information_schema.innodb_trx trx
              inner join information_schema.processlist p
                  on p.id = trx.trx_mysql_thread_id
        """ % (pid, info, info)
        for db in databases:
            sql += """
              left outer join %s.connection_info
                  on p.id = %s.connection_info.connection_id and p.db = '%s'
              """ % (db, db, db)
        sql += """
            where
                (unix_timestamp() - unix_timestamp(trx.trx_started)) > longer_than_num_seconds;
            DECLARE CONTINUE HANDLER FOR SQLSTATE '02000' SET done = TRUE ;

            OPEN c_thread_id;
            REPEAT
              FETCH c_thread_id
              INTO
                  v_host,
                  v_db,
                  v_command,
                  v_state,
                  v_info,
                  v_pid,
                  v_line1,
                  v_line2,
                  v_trx_id,
                  v_trx_query,
                  v_started,
                  v_thread_id;
              IF NOT done THEN
                SET _txns_killed = CONCAT_WS('\n', _txns_killed, CONCAT_WS(',',
                    QUOTE(v_host),
                    QUOTE(coalesce(v_db,'')),
                    QUOTE(v_command),
                    QUOTE(coalesce(v_state,'')),
                    QUOTE(coalesce(v_info,'')),
                    QUOTE(coalesce(v_pid,'')),
                    QUOTE(coalesce(v_line1,'')),
                    QUOTE(coalesce(v_line2,'')),
                    QUOTE(v_trx_id),
                    QUOTE(coalesce(v_trx_query,'')),
                    QUOTE(v_started),
                    QUOTE(v_thread_id)));
                IF 'KILL' = upper(action) THEN
                  KILL v_thread_id;
                END IF;
                SET _txns_count = _txns_count + 1;
              END IF;
            UNTIL done END REPEAT;

            IF _txns_count < 1 THEN
              SET _txns_killed = 'None';
            END IF;

            SELECT _txns_killed;

          END //
        DELIMITER ;

        DROP EVENT IF EXISTS kill_long_running_txns;
        """
        stdout, stderr = self._zendb('mysql', sql)
        if not silent:
            LOG.info("Installed mysql.KillTransactions stored procedure.")


    def check(self, minutes=360):
        sql = "call mysql.KillTransactions(%d,'DRYRUN');" % (minutes * 60,)
        stdout, stderr = self._zendb('mysql', sql)
        stdout = stdout.strip()
        if stdout != "None":
            lines = re.split("\\\\n",stdout)
            for line in lines:
                LOG.info("FOUND: %s", line)

    def kill(self, minutes=360):
        sql = "call mysql.KillTransactions(%d,'KILL');" % (minutes * 60,)
        stdout, stderr = self._zendb('mysql', sql)
        stdout = stdout.strip()
        if stdout != "None":
            lines = re.split("\\\\n",stdout)
            for line in lines:
                LOG.warn("KILLED: %s", line)

    def _zendb(self, dbname, sql):
        zendb = zenPath("Products", "ZenUtils", "ZenDB.py")
        cmd = [zendb, "--usedb", "zodb", "--useadmin", "--dbname", dbname]

        if dbname == 'mysql':
            cmd += ["--dbuser", "root", "--dbpass", ""]
        s = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = s.communicate(sql)
        if s.returncode != 0:
            LOG.error("Error executing zendb: %s %s\n" % (stdout, stderr))
            sys.exit(1)
        else:
            return (stdout, stderr)


if __name__=="__main__":
    
    usage = "Usage: %prog [install|nstall-silent|check|kill]"
    epilog = "Checks for (or kills) long-running database transactions."
    parser = OptionParser(usage=usage, epilog=epilog)
    parser.add_option("-m", "--minutes",
        dest="minutes", default=360, type="int",
        help='minutes before a transaction is considered "long-running"')
    parser.add_option("-d", "--database",
        dest="databases", default=[], action="append",
        help='which database to use. ("-d foo -d bar" for multiple databases)')
    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.print_usage()
        sys.exit(1)

    action = args[0]
    if action == 'install':
        main = Main()
        main.install(databases=options.databases)
    elif action == 'install-silent':
        main = Main()
        main.install(databases=options.databases, silent=True)
    elif action == 'check':
        main = Main()
        main.check(minutes=options.minutes)
    elif action == 'kill':
        main = Main()
        main.kill(minutes=options.minutes)
    else:
        parser.print_usage()
        sys.exit(1)

